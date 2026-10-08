from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestEquipmentCategory(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.Category = cls.env['equipment.category']
        cls.Item = cls.env['equipment.item']

        cls.root_category = cls.Category.create({
            'name': 'Laptops',
        })

        cls.child_category = cls.Category.create({
            'name': 'Dell',
            'parent_id': cls.root_category.id,
        })



    def test_category_creation(self):
        category = self.Category.create({
            'name': 'Monitors',
        })

        self.assertEqual(category.name, 'Monitors')
        self.assertEqual(category.complete_name, 'Monitors')
        self.assertFalse(category.parent_id)


    def test_complete_name(self):
        self.assertEqual(
            self.root_category.complete_name,
            'Laptops',
        )

        self.assertEqual(
            self.child_category.complete_name,
            'Laptops / Dell',
        )

    def test_deep_complete_name(self):
        third_category = self.Category.create({
            'name': 'UltraSharp',
            'parent_id': self.child_category.id,
        })

        self.assertEqual(
            third_category.complete_name,
            'Laptops / Dell / UltraSharp',
        )

    def test_parent_child_relationship(self):
        self.assertIn(
            self.child_category,
            self.root_category.child_ids,
        )

        self.assertEqual(
            self.child_category.parent_id,
            self.root_category,
        )

    def test_category_cycle_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.root_category.write({
                'parent_id': self.child_category.id,
            })

    def test_item_count_includes_child_categories(self):
        self.Item.create({
            'name': 'Dell Laptop 1',
            'category_id': self.child_category.id,
        })

        self.Item.create({
            'name': 'Dell Laptop 2',
            'category_id': self.child_category.id,
        })

        self.Item.create({
            'name': 'Laptop 3',
            'category_id': self.root_category.id,
        })

        self.assertEqual(
            self.child_category.item_count,
            2,
        )

        self.assertEqual(
            self.root_category.item_count,
            3,
        )

    # Testing smart button
    def test_action_view_items(self):
        action = self.root_category.action_view_items()

        self.assertEqual(
            action['type'],
            'ir.actions.act_window',
        )

        self.assertEqual(
            action['res_model'],
            'equipment.item',
        )

        self.assertEqual(
            action['domain'],
            [('category_id', '=', self.root_category.id)],
        )