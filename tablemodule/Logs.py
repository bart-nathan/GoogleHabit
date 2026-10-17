from tablemodule.AbstractTableModule import AbstractTableModule
from tablemodule import exec_db

class Logs(AbstractTableModule):
    
    def __init__(self):
        insert = "insert into Logs (log_date,habit_id) values (?,?)" 
        update = "update Logs set log_date = ? where log_id = ? "
        select = "select * from Logs where habit_id = ? order by log_date desc"
        select_one = "select * from Logs where log_id = ?"
        delete = "delete from Logs where log_id = ?"

        super().__init__(insert, update, select, select_one, delete)

    def select_by_habit(self, habit_id):
        return self.select((habit_id,))

    def find_by_habit_and_date(self, habit_id, log_date):
        return exec_db("select * from Logs where habit_id = ? and log_date = ?", (habit_id, log_date))

    def delete_by_habit(self, habit_id):
        return exec_db("delete from Logs where habit_id = ?", (habit_id,))

    def delete_by_habit_and_date(self, habit_id, log_date):
        return exec_db("delete from Logs where habit_id = ? and log_date = ?", (habit_id, log_date))
