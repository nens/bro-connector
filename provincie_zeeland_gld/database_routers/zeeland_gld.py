class PostgresRouter:
    def db_for_read(self, model, **hints):
        return model._meta.schema

    def db_for_write(self, model, **hints):
        return model._meta.schema

    def allow_relation(self, obj1, obj2, **hints):
        return None
    
    def allow_syncdb(self, db, model):
        if db == 'postgres' or model._meta.app_label == "zeeland_gld":
            return False  # we're not using syncdb on our legacy database
        else:  # but all other models/databases are fine
            return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'zeeland_gld':
            return None
        return None
