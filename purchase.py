import math
from decimal import Decimal

# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
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
            })
    package_quantity = fields.Function(fields.Integer('Package Quantity',
            states={
                'invisible': ~Eval('product_has_packages', False),
                'required': Eval('product_has_packages', False),
                'readonly': Eval('purchase_state') != 'draft',
                }),
        'on_change_with_package_quantity', setter='set_package_quantity')

    @fields.depends('product_package', 'quantity', 'unit', 'product')
    def on_change_with_package_quantity(self, name=None):
        package_quantity = None
        if self.product_package and self.quantity is not None:
            package_unit = self.product_package.unit
            if not package_unit and self.product:
                package_unit = self.product.default_uom
            if self.unit and package_unit:
                Uom = Pool().get('product.uom')
                quantity = Uom.compute_qty(
                    self.unit, self.quantity, package_unit)
                value = (Decimal(str(quantity)) /
                    Decimal(str(self.product_package.quantity)))
                if value == value.to_integral_value():
                    package_quantity = int(value)
        return package_quantity

    @classmethod
    def set_package_quantity(cls, lines, name, value):
        to_write = []
        for line in lines:
            if not line.product_package or value is None:
                continue
            quantity = value * line.product_package.quantity
            if line.unit:
                quantity = round(float(quantity), line.unit.digits)
            to_write.extend(([line], {'quantity': quantity}))
        if to_write:
            cls.write(*to_write)

    @fields.depends('product_package', 'quantity', 'product', 'package_quantity')
    def pre_validate(self):
        try:
            super(PurchaseLine, self).pre_validate()
        except AttributeError:
            pass
        if (self.product_package
                and Transaction().context.get('validate_package', True)):
            package_quantity = ((self.quantity or 0.0) /
                self.product_package.quantity)
            expected = abs(float(round(package_quantity, 8)))
            current = abs(self.package_quantity or 0)
            if expected != current:
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
            if self.product_supplier:
                self.product_package = self.product_supplier.get_purchase_package()
            if not self.product_package:
                self.product_package = self.product.get_purchase_package()

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

    @fields.depends('product_package', 'package_quantity', 'quantity', 'unit',
        methods=['on_change_quantity', 'on_change_with_delivery_date'])
    def on_change_package_quantity(self):
        if self.product_package and self.package_quantity is not None:
            self.quantity = round((float(self.package_quantity) *
                self.product_package.quantity), self.unit.digits)
            self.on_change_quantity()
            self.amount = self.on_change_with_amount()
            self.delivery_date = self.on_change_with_delivery_date()


class PurchaseLineStockProductPackage(metaclass=PoolMeta):
    __name__ = 'purchase.line'

    def get_move(self, move_type):
        move = super().get_move(move_type)
        move.product_package = self.product_package
        return move


class PurchaseRequest(metaclass=PoolMeta):
    __name__ = 'purchase.request'

    product_package = fields.Many2One(
        'product.package', 'Package',
        domain=[
            ['OR',
                ('template.products', '=', Eval('product', 0)),
                ('product', '=', Eval('product', 0)),
                ],
            ],
        states={
            'readonly': Eval('state') != 'draft',
            },
        depends=['product'])

    @classmethod
    def create(cls, vlist):
        requests = super().create(vlist)
        to_write = []
        for request in requests:
            if not request.product_package:
                package = request._get_supplier_package()
                if package:
                    to_write.extend(([request], {
                        'product_package': package.id,
                        }))
        if to_write:
            cls.write(*to_write)
        return requests

    @fields.depends('product', 'party')
    def on_change_product(self):
        try:
            super().on_change_product()
        except AttributeError:
            pass
        self.product_package = self._get_supplier_package()

    @fields.depends('product', 'party')
    def on_change_party(self):
        try:
            super().on_change_party()
        except AttributeError:
            pass
        self.product_package = self._get_supplier_package()

    def _get_supplier_package(self):
        if not self.product:
            return None
        for supplier in self.product.product_suppliers_used():
            if supplier.party == self.party:
                return supplier.get_purchase_package()

class CreatePurchase(metaclass=PoolMeta):
    __name__ = 'purchase.request.create_purchase'

    def _group_purchase_line_key(self, request):
        key = super()._group_purchase_line_key(request)
        return key + (('product_package', request.product_package),)

    @classmethod
    def compute_purchase_line(cls, key, requests, purchase):
        line = super().compute_purchase_line(key, requests, purchase)
        package = requests[0].product_package
        if package:
            line.product_package = package
            Uom = Pool().get('product.uom')
            package_unit = (package.product.default_uom
                if package.product else package.template.default_uom)
            package_quantity = Uom.compute_qty(
                package_unit, package.quantity, line.unit, round=False)
            line.quantity = line.unit.ceil(
                math.ceil(line.quantity / package_quantity)
                * package_quantity)
        return line


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
