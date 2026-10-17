from abc import ABC, abstractmethod
from tablemodule import exec_db

class AbstractTableModule:

    def __init__(self,insert_sql, update_sql, select_sql, select_one_sql,delete_sql):

        self.__insert_sql = insert_sql
        self.__update_sql  = update_sql
        self.__select_sql = select_sql
        self.__select_one_sql = select_one_sql
        self.__delete_sql = delete_sql

    def insert(self,params):
        exec_db(self.__insert_sql,params)

    def update(self,params):
        exec_db(self.__update_sql,params)

    def select_one(self,params):
        return exec_db(self.__select_one_sql,params)

    def select(self, params=()):
        return exec_db(self.__select_sql, params)

    def delete(self,params):
        return exec_db(self.__delete_sql,params)

    """

    @abstractmethod
    def create_table(self):
        pass

    """