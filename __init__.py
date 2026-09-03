# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import product
from . import purchase


def register():
    Pool.register(
        product.Package,
        product.Template,
        product.Product,
        product.ProductSupplier,
        purchase.PurchaseLine,
        purchase.PurchaseRequest,
        module='purchase_product_package', type_='model')
    Pool.register(
        purchase.PurchaseLineStockProductPackage,
        depends=['stock_product_package'],
        module='purchase_product_package', type_='model')
    Pool.register(
        purchase.CreatePurchase,
        purchase.HandleShipmentException,
        purchase.HandleInvoiceException,
        module='purchase_product_package', type_='wizard')
