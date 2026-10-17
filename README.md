# GoogleHabit

A modern Linux desktop Habit Tracker GUI built with **PyGTK4** (`Gtk 4.0`), using the project's **`tablemodule`** SQLite data access architecture.

## Architecture

The project follows the Table Module pattern:

- **`tablemodule/`**:
  - `AbstractTableModule.py`: Base class providing standard CRUD operations (`insert`, `update`, `select`, `select_one`, `delete`).
  - `Habits.py`: Table module representing the `Habits` table (`habit_id`, `habit_title`, `habit_description`).
  - `Logs.py`: Table module representing the `Logs` completion history table (`log_id`, `log_date`, `habit_id`).
  - `__init__.py`: Database connection manager and schema initialization (`habit.db`).
- **`app.py`**:
  - GTK4 graphical application (`HabitApplication`, `HabitWindow`).
  - Interactive master-detail UI with sidebar search and filters.
  - Quick check-ins directly from the habit list.
  - Detail pane with stats overview (current streak, best streak, total check-ins, last completed date).
  - Interactive 7-day completion activity strip.
  - Manual past date logger and log history list with deletion controls.
  - Habit creation and editing dialogs with title and description support.

## Running the Application

Ensure you have PyGObject and GTK 4 installed on your system. Run:

```bash
python3 app.py
```

Or make it directly executable:

```bash
./app.py
```
