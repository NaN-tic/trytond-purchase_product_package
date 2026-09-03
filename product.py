# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, If
from trytond.tools import grouped_slice


class Package(metaclass=PoolMeta):
    __name__ = 'product.package'

    @classmethod
    def __setup__(cls):
        super(Package, cls).__setup__()
        cls._create_package.append(
            ('purchase.line', 'purchase_product_package.msg_product_package_null'),
            )

    @classmethod
    def find_packages(cls, records):
        find_packages = super(Package, cls).find_packages(records)
        if find_packages:
            return find_packages

        Line = Pool().get('purchase.line')
        for sub_records in grouped_slice(records):
            lines = Line.search([
                    ('product_package', 'in', list(map(int, sub_records))),
                    ],
                limit=1, order=[])
            if lines:
                return lines
        return False


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'

    default_purchase_package = fields.Many2One(
        'product.package', 'Default Purchase Package',
        domain=[
            ('template', '=', Eval('id', -1)),
            ],
        states={
            'invisible': ~Eval('purchasable', False),
            },
        depends=['purchasable'])

    def get_purchase_package(self):
        return self.default_purchase_package or self.default_package


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    default_purchase_package = fields.Many2One(
        'product.package', 'Default Purchase Package',
        domain=[
            ['OR',
                ('template', '=', Eval('template', -1)),
                ('product', '=', Eval('id', -1)),
                ],
            ],
        states={
            'invisible': ~Eval('purchasable', False),
            },
        depends=['template', 'purchasable'])

    def get_purchase_package(self):
        return self.default_purchase_package or self.template.get_purchase_package()


class ProductSupplier(metaclass=PoolMeta):
    __name__ = 'purchase.product_supplier'

    default_supplier_package = fields.Many2One(
        'product.package', 'Default Supplier Package',
        domain=[If(Bool(Eval('product', -1)), [
                'OR',
                ('template', '=', Eval('template', -1)),
                ('product', '=', Eval('product', -1)),
                ], [
                ('template', '=', Eval('template', -1)),
                ])],
        depends=['template', 'product'])

    def get_purchase_package(self):
        if self.default_supplier_package:
            return self.default_supplier_package
        if self.product:
            return self.product.get_purchase_package()
        return self.template.get_purchase_package()
