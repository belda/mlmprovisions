import decimal
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from mlmtools.models import MarketerNode, TrackCode, CodeUse, DummyTarget


class ProvisionIntegrityTestCase(TestCase):
    DS,DU = datetime.fromisoformat("1990-01-01"), datetime.fromisoformat("2100-01-01")
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password="12345")
        self.top_node = MarketerNode.objects.create(name="Top Base", split_type="fixed", split_cut=60,
                                               owner=self.user )
        self.l2_marketeri1 = MarketerNode.objects.create(name="Marketeri 1", split_type="fixed", split_cut=25,
                                                    owner=self.user, tn_parent=self.top_node )
        self.l3_sub1 = MarketerNode.objects.create(name="second sub1", split_type="treesplit", split_cut=25,
                                              owner=self.user, tn_parent=self.l2_marketeri1)
        self.l4_sub = MarketerNode.objects.create(name="L4 sub", split_type="treesplit", split_cut=25,
                                            owner=self.user, tn_parent=self.l3_sub1)
        self.l5_sub = MarketerNode.objects.create(name="L5 sub", split_type="treesplit", split_cut=25,
                                            owner=self.user, tn_parent=self.l4_sub)
        self.l2_marketeri2 = MarketerNode.objects.create(name="Marketeri 2", split_type="fixed", split_cut=0,
                                                    owner=self.user, tn_parent=self.top_node)

        self.test_client = User.objects.create_user(username='testclient', password="12345")
        self.test_code_l5_sub = TrackCode.objects.create(code="L5SUB1", usage="useronce", discount_type="perc", discount=0,
                                                         node=self.l5_sub)
        self.dummy_order1 = DummyTarget.objects.create(name="dummy target1", amount=1000.0)

        self.test_code_l5_sub2 = TrackCode.objects.create(code="L5SUB2", usage="useronce", discount_type="perc", discount=10,
                                                          node=self.l5_sub)
        self.test_code_l4_sub = TrackCode.objects.create(code="L4SUB1", usage="useronce", discount_type="perc", discount=10,
                                                         node=self.l4_sub)
        self.cu_simple_treesplit_no_discount = CodeUse.objects.create(code=self.test_code_l5_sub, content_object=self.dummy_order1, user=self.test_client, amount=self.dummy_order1.amount)
        self.cu_simple_treesplit_discount = CodeUse.objects.create(code=self.test_code_l5_sub2, content_object=self.dummy_order1, user=self.test_client, amount=self.dummy_order1.amount)
        self.cu_simple_treesplit_l4_discount = CodeUse.objects.create(code=self.test_code_l4_sub, content_object=self.dummy_order1, user=self.test_client, amount=self.dummy_order1.amount)

        self.test_code_l2_sub2 = TrackCode.objects.create(code="L2SUB2", usage="always", discount_type="perc", discount=20,
                                                         node=self.l2_marketeri2)
        self.cu_side = CodeUse.objects.create(code=self.test_code_l2_sub2, content_object=self.dummy_order1, user=self.test_client, amount=self.dummy_order1.amount)


    def test_min_provision(self):
        assert self.l5_sub.provision_min(100)==22.5, "Min provision not matching expected value"
        assert self.l4_sub.provision_min(100) == 5.625, "Min provision not matching expected value"
        assert self.l3_sub1.provision_min(100) == 1.875, "Min provision not matching expected value"
        assert self.l2_marketeri1.provision_min(100) == 10.0, "Min provision not matching expected value"
        assert self.top_node.provision_min(100) == 40.0, "Min provision not matching expected value"

    def test_max_available(self):
        assert self.l5_sub.max_available(100) == 30.0, "Max provision not matching expected value"
        assert self.l4_sub.max_available(100) == 30.0, "Max provision not matching expected value"
        assert self.l3_sub1.max_available(100) == 30.0, "Max provision not matching expected value"
        assert self.l2_marketeri1.max_available(100) == 40.0, "Max provision not matching expected value"
        assert self.top_node.max_available(100) == 100.0, "Max provision not matching expected value"

    def test_simple_treesplit_no_discount(self):
        cu = self.cu_simple_treesplit_no_discount
        assert cu.amount == cu.control_sum, "Original amount and control sum do not match"
        assert cu.discounted_amount == 0.0, "Discount is not 0"
        assert cu.get_provision() == self.l5_sub.my_cut(self.dummy_order1.amount), "The personal cut should be same as the provision if no discount"
        ap = [x for x in cu.get_ancestor_provisions()]
        assert ap[0][0] == self.top_node      and ap[0][1] == Decimal(600), "Wrong provision or node"
        assert ap[1][0] == self.l2_marketeri1 and ap[1][1] == Decimal(100), "Wrong provision or node"
        assert ap[2][0] == self.l3_sub1       and ap[2][1] == Decimal(18.75), "Wrong provision or node"
        assert ap[3][0] == self.l4_sub        and ap[3][1] == Decimal(56.25), "Wrong provision or node"
        assert ap[4][0] == self.l5_sub        and ap[4][1] == Decimal(225), "Wrong provision or node"

    def test_simple_treesplit_discount(self):
        cu = self.cu_simple_treesplit_discount
        assert cu.amount == cu.control_sum, "Original amount and control sum do not match"
        assert cu.discounted_amount == 100.0, "Discount is not 100"
        ap = [x for x in cu.get_ancestor_provisions()]
        assert ap[0][0] == self.top_node      and ap[0][1] == Decimal(600), "Wrong provision or node"
        assert ap[1][0] == self.l2_marketeri1 and ap[1][1] == Decimal(100), "Wrong provision or node"
        assert ap[2][0] == self.l3_sub1       and ap[2][1] == Decimal(18.75), "Wrong provision or node"
        assert ap[3][0] == self.l4_sub        and ap[3][1] == Decimal(56.25), "Wrong provision or node"
        assert ap[4][0] == self.l5_sub        and ap[4][1] == Decimal(125), "Wrong provision or node"

    def test_simple_treesplit_l4_discount(self):
        cu = self.cu_simple_treesplit_l4_discount
        assert cu.amount == cu.control_sum, "Original amount and control sum do not match"
        assert cu.discounted_amount == 100.0, "Discount is not 100"
        ap = [x for x in cu.get_ancestor_provisions()]
        assert ap[0][0] == self.top_node      and ap[0][1] == Decimal(600), "Wrong provision or node"
        assert ap[1][0] == self.l2_marketeri1 and ap[1][1] == Decimal(100), "Wrong provision or node"
        assert ap[2][0] == self.l3_sub1       and ap[2][1] == Decimal(75), "Wrong provision or node"
        assert ap[3][0] == self.l4_sub        and ap[3][1] == Decimal(125), "Wrong provision or node"

    def sppp(self, node, expected_value):
        node.refresh_from_db()
        val = node.get_sum_provisions_for_period(self.DS, self.DU)
        assert val == expected_value, "%s has sum %.2f, but expected %.2f" % (node, val, expected_value)

    def test_provision_totals(self):
        self.sppp(self.top_node, 2400)
        self.sppp(self.l2_marketeri1, 300)
        self.sppp(self.l3_sub1, 112.5)
        self.sppp(self.l4_sub, 237.5)
        self.sppp(self.l5_sub, 350)


    def test_provision_subtree_l4(self):
        self.l4_sub.refresh_from_db()
        prov_tree = self.l4_sub.get_provisions_tree_for_period(self.DS, self.DU)
        assert prov_tree[0][0] == self.l4_sub and prov_tree[0][2] == 125.0
        assert prov_tree[1][0] == self.l5_sub and prov_tree[1][2] == 112.5

    def test_provision_subtree_l3(self):
        self.l3_sub1.refresh_from_db()
        prov_tree = self.l3_sub1.get_provisions_tree_for_period(self.DS, self.DU)
        assert prov_tree[0][0] == self.l3_sub1 and prov_tree[0][2] == 0 #nothing just for myself
        assert prov_tree[1][0] == self.l4_sub and prov_tree[1][2] == 75
        assert prov_tree[2][0] == self.l5_sub and prov_tree[2][2] == 37.5


class DiscountCodeTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password="12345")
        self.user2 = User.objects.create_user(username='testuser2', password="12345")
        self.user3 = User.objects.create_user(username='testuser3', password="12345")
        self.top_node = MarketerNode.objects.create(name="Top Base", split_type="fixed", split_cut=60, owner=self.user )
        self.code_always_1 = TrackCode.objects.create(code="ALWAYS1", usage="always", discount_type="perc", discount=30, node=self.top_node)
        self.code_always_2 = TrackCode.objects.create(code="ALWAYS2", usage="always", discount_type="perc", discount=30, node=self.top_node)
        self.code_useronce_1 = TrackCode.objects.create(code="USER1", usage="useronce", discount_type="perc", discount=30, node=self.top_node)
        self.code_useronce_2 = TrackCode.objects.create(code="USER2", usage="useronce", discount_type="perc", discount=30, node=self.top_node)
        self.code_user_n_2 = TrackCode.objects.create(code="UN2", usage="useronce", discount_type="perc", max_n=2, discount=30, node=self.top_node)
        self.code_once_1 = TrackCode.objects.create(code="ONCE1", usage="once", discount_type="perc", discount=30, node=self.top_node)
        self.code_once_2 = TrackCode.objects.create(code="ONCE2", usage="once", discount_type="perc", discount=30, node=self.top_node)
        self.code_n_2 = TrackCode.objects.create(code="N2", usage="once", discount_type="perc", max_n=2, discount=30, node=self.top_node)


    def test_once(self):
        self.assertEqual((True, 30), CodeUse.test_use(self.code_once_1, self.user, target=None, amount=100))
        CodeUse.use(self.code_once_1, self.user, target=None, amount=100)
        self.assertEqual((False, 30), CodeUse.test_use(self.code_once_1, self.user, target=None, amount=100))
        self.assertEqual((False, 30), CodeUse.test_use(self.code_once_1, self.user2, target=None, amount=100))

        self.assertEqual((True, 30), CodeUse.test_use(self.code_useronce_1, self.user, target=None, amount=100))
        CodeUse.use(self.code_useronce_1, self.user, target=None, amount=100)
        self.assertEqual((False, 30), CodeUse.test_use(self.code_useronce_1, self.user, target=None, amount=100))
        self.assertEqual((True, 30), CodeUse.test_use(self.code_useronce_1, self.user2, target=None, amount=100))

    def test_max_n(self):
        self.assertEqual((True, 30), CodeUse.test_use(self.code_n_2, self.user, target=None, amount=100))
        CodeUse.use(self.code_n_2, self.user, target=None, amount=100)
        self.assertEqual((True, 30), CodeUse.test_use(self.code_n_2, self.user, target=None, amount=100))
        self.assertEqual((True, 30), CodeUse.test_use(self.code_n_2, self.user2, target=None, amount=100))
        CodeUse.use(self.code_n_2, self.user2, target=None, amount=100)
        self.assertEqual((False, 30), CodeUse.test_use(self.code_n_2, self.user, target=None, amount=100))
        self.assertEqual((False, 30), CodeUse.test_use(self.code_n_2, self.user2, target=None, amount=100))

        self.assertEqual((True, 30), CodeUse.test_use(self.code_user_n_2, self.user, target=None, amount=100))
        CodeUse.use(self.code_user_n_2, self.user, target=None, amount=100)
        self.assertEqual((True, 30), CodeUse.test_use(self.code_user_n_2, self.user, target=None, amount=100))
        self.assertEqual((True, 30), CodeUse.test_use(self.code_user_n_2, self.user2, target=None, amount=100))
        CodeUse.use(self.code_user_n_2, self.user2, target=None, amount=100)
        self.assertEqual((True, 30), CodeUse.test_use(self.code_user_n_2, self.user, target=None, amount=100))
        self.assertEqual((True, 30), CodeUse.test_use(self.code_user_n_2, self.user2, target=None, amount=100))
        CodeUse.use(self.code_user_n_2, self.user, target=None, amount=100)
        self.assertEqual((False, 30), CodeUse.test_use(self.code_user_n_2, self.user, target=None, amount=100))
        self.assertEqual((True, 30), CodeUse.test_use(self.code_user_n_2, self.user2, target=None, amount=100))


    def test_always(self):
        self.assertEqual((True, 30), CodeUse.test_use(self.code_always_1, self.user, target=None, amount=100))
        CodeUse.use(self.code_always_1, self.user, target=None, amount=100)
        CodeUse.use(self.code_always_1, self.user, target=None, amount=100)
        CodeUse.use(self.code_always_1, self.user2, target=None, amount=100)
        CodeUse.use(self.code_always_1, self.user2, target=None, amount=100)
        CodeUse.use(self.code_always_1, self.user, target=None, amount=100)
        CodeUse.use(self.code_always_1, self.user, target=None, amount=100)
        CodeUse.use(self.code_always_1, self.user2, target=None, amount=100)
        CodeUse.use(self.code_always_1, self.user2, target=None, amount=100)
        self.assertEqual((True, 30), CodeUse.test_use(self.code_always_1, self.user, target=None, amount=100))


    def test_validity(self):
        self.code_not_yet_valid = TrackCode.objects.create(code="VV1", usage="always", discount_type="perc", discount=30, node=self.top_node,
                                                            valid_from="2100-01-01", valid_until="2199-01-01")
        self.assertEqual((False, 30), CodeUse.test_use(self.code_not_yet_valid, self.user, target=None, amount=100))

        self.code_no_longer_valid = TrackCode.objects.create(code="VV2", usage="always", discount_type="perc", discount=30, node=self.top_node,
                                                            valid_from="1970-01-01", valid_until="1999-01-01")
        self.assertEqual((False, 30), CodeUse.test_use(self.code_no_longer_valid, self.user, target=None, amount=100))
        self.code_valid = TrackCode.objects.create(code="VV3", usage="always", discount_type="perc", discount=30, node=self.top_node,
                                                            valid_from="1970-01-01", valid_until="2999-01-01")
        self.assertEqual((True, 30), CodeUse.test_use(self.code_valid, self.user, target=None, amount=100))
