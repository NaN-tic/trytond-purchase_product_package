# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.i18n import gettext
from trytond.exceptions import UserError


class PurchaseLine(metaclass=PoolMeta):
    __name__ = 'purchase.line'

    product_has_packages = fields.Function(fields.Boolean(
            'Product Has packages'),
        'on_change_with_product_has_packages')
    product_template = fields.Function(fields.Many2One('product.template',
            'Product Has packages', context={
                'company': Eval('company', -1),
            }, depends=['company']),
        'on_change_with_product_template')
    product_package = fields.Many2One('product.package', 'Package',
        domain=[
            ['OR',
                ('template', '=', Eval('product_template', 0)),
                ('product', '=', Eval('product', 0)),]
        ],
        states={
            'invisible': ~Eval('product_has_packages', False),
            'required': Eval('product_has_packages', False),
            'readonly': Eval('purchase_state') != 'draft',
            },
        depends=['product_template', 'product_has_packages', 'purchase_state',
            'product',])
    package_quantity = fields.Integer('Package Quantity',
        states={
            'invisible': ~Eval('product_has_packages', False),
            'required': Eval('product_has_packages', False),
            'readonly': Eval('purchase_state') != 'draft',
            },
        depends=['product_has_packages', 'purchase_state'])

    @fields.depends('product_package', 'quantity', 'product_package',
        'product', 'package_quantity')
    def pre_validate(self):
        try:
            super(PurchaseLine, self).pre_validate()
        except AttributeError:
            pass
        if (self.product_package
                and Transaction().context.get('validate_package', True)):
            package_quantity = ((self.quantity or 0.0) /
                self.product_package.quantity)
            if abs(float(round(package_quantity, 8))) != abs(self.package_quantity):
                raise UserError(gettext(
                    'purchase_product_package.msg_package_quantity',
                    qty=self.quantity,
                    product=self.product.rec_name,
                    package=self.product_package.rec_name,
                    package_qty=self.product_package.quantity))

    @fields.depends('product')
    def on_change_product(self):
        super(PurchaseLine, self).on_change_product()
        self.product_package = None
        if self.product:
            # Check if we have a product.package (product.product level)
            for package in self.product.packages:
                if package.is_default:
                    self.product_package = package
                    break
            if not self.product_package:
                # If we dont have a default value in (product.product) we try
                # to search at template level (product.template)
                for package in self.product.template.packages:
                    if package.is_default:
                        self.product_package = package
                        break

    @fields.depends('product', 'product_supplier')
    def on_change_with_product_has_packages(self, name=None):
        if self.product and (self.product.template.packages or
                self.product.packages):
            return True
        return False

    @fields.depends('product', 'product_supplier')
    def on_change_with_product_template(self, name=None):
        if self.product:
            return self.product.template.id
        return None

    @fields.depends('product_package')
    def on_change_product_package(self):
        if not self.product_package:
            self.quantity = None
            self.package_quantity = None

    @fields.depends('product_package', 'package_quantity', 'unit_price',
        'type', methods=['on_change_quantity', 'on_change_with_delivery_date'])
    def on_change_package_quantity(self):
        if self.product_package and self.package_quantity:
            self.quantity = (float(self.package_quantity) *
                self.product_package.quantity)
            self.on_change_quantity()
            self.amount = self.on_change_with_amount()
            self.delivery_date = self.on_change_with_delivery_date()

    @fields.depends('product_package', 'quantity')
    def on_change_quantity(self):
        super(PurchaseLine, self).on_change_quantity()
        if self.product_package and self.quantity:
            self.package_quantity = int(self.quantity /
                self.product_package.quantity)


class HandleShipmentException(metaclass=PoolMeta):
    __name__ = 'purchase.handle.shipment.exception'

    def transition_handle(self):
        with Transaction().set_context(validate_package=False):
            return super(HandleShipmentException, self).transition_handle()


class HandleInvoiceException(metaclass=PoolMeta):
    __name__ = 'purchase.handle.invoice.exception'

    def transition_handle(self):
        with Transaction().set_context(validate_package=False):
            return super(HandleInvoiceException, self).transition_handle()
