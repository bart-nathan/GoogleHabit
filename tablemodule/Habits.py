from tablemodule.AbstractTableModule import AbstractTableModule
from tablemodule import exec_db

class Habits(AbstractTableModule):
    
    def __init__(self):
        insert = "insert into Habits (habit_title, habit_description) values (?,?)"
        update = "update Habits set habit_title = ?, habit_description = ? where habit_id = ?"
        select = "select * from Habits order by habit_title"
        select_one = "select * from Habits where habit_id = ?"
        delete = "delete from Habits where habit_id = ?"

        super().__init__(insert, update, select, select_one, delete)

    def search(self, query):
        pattern = f"%{query}%"
        return exec_db("select * from Habits where habit_title like ? or habit_description like ? order by habit_title", (pattern, pattern))
