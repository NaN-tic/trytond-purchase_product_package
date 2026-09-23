if 'pool' not in globals():
    # Prevent pyflakes warnings when the script is not executed by Tryton.
    pool = None
    transaction = None


Configuration = pool.get('purchase.configuration')
# Creating a missing singleton requires the table lock from the start of
# the transaction. The console does not retry TransactionError exceptions.
with transaction.new_transaction(
        _lock_tables=[Configuration._table]) as configuration_transaction:
    configuration = Configuration(1)
    configuration.package_required = True
    configuration.save()
    configuration_transaction.commit()
