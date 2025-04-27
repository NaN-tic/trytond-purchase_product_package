import unittest
from decimal import Decimal

from proteus import Model
from trytond.exceptions import UserError
from trytond.modules.account.tests.tools import (create_chart,
                                                 create_fiscalyear,
                                                 get_accounts)
from trytond.modules.account_invoice.tests.tools import (
    create_payment_term, set_fiscalyear_invoice_sequences)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install purchase
        config = activate_modules('purchase_product_package')

        # Create company
        _ = create_company()
        company = get_company()

        # Create purchase user
        User = Model.get('res.user')
        Group = Model.get('res.group')
        purchase_user = User()
        purchase_user.name = 'Purchase'
        purchase_user.login = 'purchase'
        purchase_group, = Group.find([('name', '=', 'Purchase')])
        purchase_user.groups.append(purchase_group)
        purchase_user.save()

        # Create stock user
        stock_user = User()
        stock_user.name = 'Stock'
        stock_user.login = 'stock'
        stock_group, = Group.find([('name', '=', 'Stock')])
        stock_user.groups.append(stock_group)
        stock_user.save()

        # Create account user
        account_user = User()
        account_user.name = 'Account'
        account_user.login = 'account'
        account_group, = Group.find([('name', '=', 'Accounting')])
        account_user.groups.append(account_group)
        account_user.save()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']

        # Create parties
        Party = Model.get('party.party')
        supplier = Party(name='Supplier')
        supplier.save()
        customer = Party(name='Customer')
        customer.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        Product = Model.get('product.product')
        product = Product()
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.purchasable = True
        template.list_price = Decimal('10')
        template.cost_price_method = 'fixed'
        template.account_category = account_category
        package = template.packages.new()
        package.name = 'Box'
        package.quantity = 6
        template.save()
        template.reload()
        package, = template.packages
        product.template = template
        product.cost_price = Decimal('5')
        product.save()

        # Create payment term
        payment_term = create_payment_term()
        payment_term.save()

        # Purchase products with package
        config.user = purchase_user.id
        Purchase = Model.get('purchase.purchase')
        purchase = Purchase()
        purchase.party = supplier
        purchase.payment_term = payment_term
        purchase.invoice_method = 'order'
        line = purchase.lines.new()
        line.product = product
        line.product_package = package
        line.package_quantity = 2
        line.unit_price = product.cost_price
        self.assertEqual(line.quantity, 12.0)
        self.assertEqual(line.amount, Decimal('60.00'))
        line.quantity = 13
        with self.assertRaises(UserError):

            purchase.save()
        line.quantity = 12
        self.assertEqual(line.package_quantity, 2)
        line.quantity = -12
        self.assertEqual(line.package_quantity, -2)
        purchase.save()
