import decimal

from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext as _
from treenode.models import TreeNodeModel
from django.utils.timezone import now


class TrackCode(models.Model):
    node = models.ForeignKey('MarketerNode', null=True, blank=True, on_delete=models.CASCADE)
    code = models.CharField(max_length=64, db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    USAGE_CHOICES = ( ("always", _("always",)),
                      ("useronce", _("Nx / user")),
                      ("once", _("Nx / user")))
    usage = models.CharField(max_length=8, choices=USAGE_CHOICES, default="useronce")
    max_n = models.PositiveIntegerField(default=1, help_text=_("The maximum number of codes applied to usage choices"))
    discount = models.DecimalField(default=10, decimal_places=2, max_digits=5)
    DISCOUNT_TYPE_CHOICES = ( ("perc", "%"),
                              ("CZK", "CZK"))
    discount_type = models.CharField(max_length=4, choices=DISCOUNT_TYPE_CHOICES, default="perc", verbose_name="dt")

    def __str__(self):
        return self.code

    @property
    def num_used(self):
        return self.codeuse_set.count()


class MarketerNode(TreeNodeModel):
    treenode_display_field = 'name'
    name              = models.CharField(max_length=256)
    owner             = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    SPLIT_TYPE_CHOICES = ( ( "fixed", _("fixed"),),
                           ( "treesplit", _("tree split")) )
    split_type        = models.CharField(max_length=16, choices=SPLIT_TYPE_CHOICES, default="fixed", help_text=_("How to split, fixed amount (1 level), or tree split (recursively sent up the tree)"))
    split_cut         = models.DecimalField(default=100.0, decimal_places=2, max_digits=5, help_text=_("% of split between THIS one and other"))
    can_have_children = models.BooleanField(default=True)

    @property
    def node_cut(self):
        return self.split_cut

    @property
    def sub_cut(self):
        return 100-self.split_cut

    def max_available(self, value=1.0):
        value = decimal.Decimal(value)
        for n in self.ancestors:
            if n.split_type == "fixed":
                value*= n.sub_cut/100
        return value

    @property
    def max_discount(self):
        return self.max_available(100)

    def my_cut(self, value=1.0):
        if self.parent == None:
            return value * self.split_cut/100
        value = self.max_available(value)
        if self.split_type == "treesplit" and self.parent and self.parent.split_type== "treesplit":
            return value * self.sub_cut/100
        return value

    def provision_min(self, value=1.0):
        if self.split_type == "treesplit":
            mc = self.max_available(value)
            for i in range(0,self.depth):
                mc-= mc*self.sub_cut/100
            if self.parent and self.parent.split_type!= "treesplit":
                return mc
            else:
                return mc*self.sub_cut/100
        else:
            value = decimal.Decimal(value)
            for n in self.ancestors:
                value*=n.sub_cut/100
            if self.parent:
                return value*self.node_cut/100
            else: #top level
                return value*self.sub_cut/100

    def save(self, *args, **kwargs):
        if self.parent and self.parent.split_type == "treesplit":
            self.split_type = self.parent.split_type
            self.split_cut = self.parent.split_cut
        for n in self.children:
            n.split_type = self.split_type
            n.split_cut = self.split_cut
            n.save()
        return super(MarketerNode, self).save(*args, **kwargs)


    def get_tree_split_ancestors(self):
        ancs = []
        if self.split_type == "treesplit":
            # yield self
            for anc in self.ancestors[::-1]:
                if anc.split_type != "treesplit":
                    break
                ancs.append(anc)
        return ancs


    def subpath(self, subnode):
        if subnode == self:
            return []
        ret = [subnode]
        for x in subnode.ancestors[::-1]:
            if x==self:
                break
            ret.append(x)
        return ret[::-1]


    def split_the_spoils(self, amount, cash_node, discount=0.0):
        ''' Splits the amount based on the tree. self is cashing and casher_node is the one who made the deal'''
        amount = decimal.Decimal(amount)
        if not self.parent:
            return amount*(self.split_cut/100)
        cut_for_node = cash_node.my_cut(100) - discount
        cash_node_cut = amount*(cut_for_node/100)
        if self==cash_node:
            return cash_node_cut
        currnode = cash_node
        if self.split_type == "treesplit":
            tree_split_ancestors = cash_node.get_tree_split_ancestors()
            upcut = cash_node.max_available(100)

            for x in tree_split_ancestors:
                upcut-= upcut*self.sub_cut/100
                if x == self and self.parent.split_type == "treesplit":
                    return amount * upcut / 100 * x.sub_cut / 100
            return amount*upcut/100
        else:
            return self.provision_min(amount)


    def get_provisions_for_period(self, start, end):
        ''' Generates report of code usage in the timeframe '''
        my_provisions = []
        scope = [self] + self.descendants
        subids = [d.id for d in self.descendants]
        for cu in CodeUse.objects.filter(code__node__in=scope).filter(used_at__gt=start, used_at__lte=end):
            cash_node = cu.code.node
            for_me = self.split_the_spoils(cu.amount, cash_node, cu.code.discount)
            my_provisions.append( (cu, for_me, self.subpath(cash_node)) )
        return my_provisions

    def get_sum_provisions_for_period(self, start, end):
        ''' Gets the total provisions for this node, from this node and its subnodes'''
        total = decimal.Decimal(0.0)
        for cu, provision, subpath in self.get_provisions_for_period(start, end):
            total+= provision
        return total

    def get_provisions_tree_for_period(self, start, end):
        ''' return list of (node, depth, individual provision, individual inherited provision, node's inherited provision)'''
        scope = [self] + self.descendants
        accumulator = {}
        for node in scope:
            if node not in accumulator:
                accumulator[node] = decimal.Decimal(0.0)
        for cu, provision, subpath in self.get_provisions_for_period(start, end):
            accumulator[cu.code.node]+= provision
        ret = [ ( self, 0, accumulator[self] ) ]
        for x in self.descendants:
            ret.append( (x, x.level-self.level, accumulator[x]) )
        return ret

class CodeUse(models.Model):
    code = models.ForeignKey(TrackCode, on_delete=models.DO_NOTHING)
    content_type = models.ForeignKey(ContentType, on_delete=models.DO_NOTHING, null=True)
    object_id = models.PositiveIntegerField(null=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    user = models.ForeignKey(User, null=True, on_delete=models.DO_NOTHING)
    used_at = models.DateTimeField(auto_now=True, db_index=True)
    amount = models.DecimalField(default=10, decimal_places=2, max_digits=10)

    def can_be_used(self):
        ''' this method should be called before save '''
        if self.code.valid_from and self.code.valid_from > now().date():
            return False
        if self.code.valid_until and self.code.valid_until <= now().date():
            return False
        if self.code.usage == "once":
            if CodeUse.objects.filter(code=self.code).count() >= self.code.max_n:
                return False
        elif self.code.usage == "useronce":
            if CodeUse.objects.filter(code=self.code, user=self.user).count() >= self.code.max_n:
                return False
        #TODO can be applied to target
        return True

    @classmethod
    def test_use(cls, code_str, user, target=None, amount=0):
        ''' Test if the string code can be used for the desired user
        :param code_str - string of the discount code
        :param user - the Django user to map to
        :param target - the object this discount is referring to (usually the Order)
        :param amount - the original amount to calculate the discount '''
        try:
            code = TrackCode.objects.get(code__iexact=code_str)
        except TrackCode.DoesNotExist:
            return False, decimal.Decimal(0.0)
        cu = CodeUse(code=code, content_object=target, user=user, amount=amount)
        return cu.can_be_used(), cu.discounted_amount

    @classmethod
    def use(cls, code_str, user, target=None, amount=0):
        ''' Test if the string code can be used for the desired user
        :param code_str - string of the discount code
        :param user - the Django user to map to
        :param target - the object this discount is referring to (usually the Order)
        :param amount - the original amount to calculate the discount '''
        code = TrackCode.objects.get(code__iexact=code_str)
        cu = CodeUse(code=code, content_object=target, user=user, amount=amount)
        assert cu.can_be_used(), "This code can not be used"
        cu.save()

    def get_provision(self):
        ''' Gets the provision for this node '''
        cash_node = self.code.node
        return cash_node.split_the_spoils(self.amount, cash_node, self.code.discount) #TODO discount type

    def get_ancestor_provisions(self):
        cash_node = self.code.node
        discount = self.code.discount
        for node in cash_node.ancestors:
            yield (node, node.split_the_spoils(self.amount, cash_node, discount))
        yield (cash_node, cash_node.split_the_spoils(self.amount, cash_node, self.code.discount))

    @property
    def discounted_amount(self):
        self.amount = decimal.Decimal(self.amount)
        return self.amount*decimal.Decimal(self.code.discount)/100

    @property
    def control_sum(self):
        ''' Sum all after spliting the spoils. (must match the original amount) '''
        sum = decimal.Decimal(0)
        for node, split in self.get_ancestor_provisions():
            sum+= split
        sum+= self.discounted_amount
        return sum


class DummyTarget(models.Model):
    name = models.CharField(max_length=2048)
    amount = models.DecimalField(decimal_places=2, max_digits=10)
    code_used = GenericRelation(CodeUse)

    def __str__(self):
        return "DummyTarget %s:%s" % (self.pk, self.name)