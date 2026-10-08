from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EquipmentCategory(models.Model):
    _name = 'equipment.category'
    _description = 'Equipment Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _parent_name = 'parent_id'
    _parent_store = True
    _order = 'complete_name'


    name = fields.Char(
        required=True, index=True, tracking=True,
        translate=True
    )
    complete_name = fields.Char(
        compute='_compute_complete_name', recursive=True, store=True,
    )

    parent_id = fields.Many2one(
        'equipment.category', ondelete='cascade',
        index=True, string='Parent Category',
    )

    parent_path = fields.Char(
        index=True, unaccent=False,
    )

    child_ids = fields.One2many(
        'equipment.category', 'parent_id',
        string='Sub-Category'
    )

    item_ids = fields.One2many(
        'equipment.item', 'category_id',
        string='Items'
    )
    item_count = fields.Integer(
        string='Items', compute='_compute_item_count',
        help="Number of items in this category, including its sub-categories."
    )



    # Compute Methods
    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = f"{category.parent_id.complete_name} / {category.name}"
            else:
                category.complete_name = category.name


    # @api.depends('item_ids')
    # def _compute_item_count(self):
    #     for category in self:
    #         category.item_count = len(category.item_ids)


    # @api.depends('parent_path')
    # def _compute_item_count(self):
    #     for category in self:
    #         category.item_count = self.env['equipment.item'].search_count([
    #             ('category_id', 'child_of', category.id),
    #         ])


    @api.depends('parent_path')
    def _compute_item_count(self):
        categories = self.filtered('id')

        if not categories:
            return

        counts = self.env['equipment.item']._read_group(
            [('category_id', 'child_of', categories.ids)],
            ['category_id'],
            ['__count'],
        )

        # print('*' * 20, '\n\n\n\n\n\n')
        #
        # print(counts)
        #
        # print('*' * 20, '\n\n\n\n\n\n')
        # print(counts)

        for category in self:
            category.item_count = sum(
                count
                for item_category, count in counts
                if item_category
                and item_category.parent_path
                and category.parent_path
                and item_category.parent_path.startswith(category.parent_path)
            )


    # Constraints
    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if self._has_cycle():
            raise ValidationError(
                _("You cannot create recursive categories.")
            )
    # Smart Buttons
    def action_view_items(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': f"{self.complete_name} Items",
            'res_model': 'equipment.item',
            'view_mode': 'list,form',
            'domain': [('category_id', '=', self.id)],
        }
