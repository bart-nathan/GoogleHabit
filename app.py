#!/usr/bin/env python3
"""
GoogleHabit - Daily Habit Tracker GUI
Built with PyGTK4 using the tablemodule data layer.
"""

import sys
import os
from datetime import date, datetime, timedelta

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gdk', '4.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango

# Ensure project root is in path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from tablemodule.Habits import Habits
from tablemodule.Logs import Logs


def calculate_streaks(date_strings, today=None):
    """
    Calculate current streak, longest streak, and whether today is completed.
    Returns: (current_streak, longest_streak, is_today_done)
    """
    if today is None:
        today = date.today()

    if not date_strings:
        return 0, 0, False

    parsed_dates = set()
    for ds in date_strings:
        try:
            parsed_dates.add(date.fromisoformat(ds))
        except (ValueError, TypeError):
            continue

    if not parsed_dates:
        return 0, 0, False

    today_done = today in parsed_dates

    # Current streak calculation:
    # If today is completed, streak starts today.
    # If today is not completed yet, streak is maintained if yesterday was completed.
    current_streak = 0
    if today_done:
        cursor = today
    elif (today - timedelta(days=1)) in parsed_dates:
        cursor = today - timedelta(days=1)
    else:
        cursor = None

    if cursor is not None:
        while cursor in parsed_dates:
            current_streak += 1
            cursor -= timedelta(days=1)

    # Longest streak calculation
    longest_streak = 0
    temp_streak = 0
    prev = None
    for d in sorted(parsed_dates):
        if prev is None or d == prev + timedelta(days=1):
            temp_streak += 1
        elif d == prev:
            pass
        else:
            temp_streak = 1
        prev = d
        if temp_streak > longest_streak:
            longest_streak = temp_streak

    return current_streak, longest_streak, today_done


def format_relative_date(iso_date_str, today=None):
    """Returns (formatted_date, relative_label)."""
    if today is None:
        today = date.today()
    try:
        d = date.fromisoformat(iso_date_str)
        formatted = d.strftime("%a, %b %d, %Y")
        delta = (today - d).days
        if delta == 0:
            rel = "Today"
        elif delta == 1:
            rel = "Yesterday"
        elif delta > 1:
            rel = f"{delta} days ago"
        elif delta == -1:
            rel = "Tomorrow"
        else:
            rel = f"In {-delta} days"
        return formatted, rel
    except Exception:
        return iso_date_str, ""


class HabitEditDialog(Gtk.Window):
    """Modal dialog for creating or editing a habit."""

    def __init__(self, parent, habit=None, on_save=None):
        super().__init__(
            title="Edit Habit" if habit else "New Habit",
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
            default_width=440,
            default_height=320,
        )
        self.habit = habit
        self.on_save = on_save

        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)

        save_label = "Save" if habit else "Create"
        save_btn = Gtk.Button(label=save_label)
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save_clicked)
        header.pack_end(save_btn)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        content.set_margin_start(20)
        content.set_margin_end(20)
        content.set_margin_top(16)
        content.set_margin_bottom(20)

        # Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        title_lbl = Gtk.Label(label="Habit Title", xalign=0.0)
        title_lbl.add_css_class("form-label")
        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("e.g., Drink 2L Water, Morning Run, Read 20 pages")
        if habit and habit[1]:
            self.title_entry.set_text(habit[1])
        self.title_entry.connect("activate", lambda e: self._on_save_clicked(None))
        title_box.append(title_lbl)
        title_box.append(self.title_entry)
        content.append(title_box)

        # Description
        desc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        desc_lbl = Gtk.Label(label="Description (Optional)", xalign=0.0)
        desc_lbl.add_css_class("form-label")
        desc_scroller = Gtk.ScrolledWindow()
        desc_scroller.set_min_content_height(100)
        desc_scroller.set_vexpand(True)
        self.desc_view = Gtk.TextView()
        self.desc_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        if habit and habit[2]:
            self.desc_view.get_buffer().set_text(habit[2])
        desc_scroller.set_child(self.desc_view)
        desc_box.append(desc_lbl)
        desc_box.append(desc_scroller)
        content.append(desc_box)

        # Error notification label
        self.error_label = Gtk.Label(label="", xalign=0.0)
        self.error_label.add_css_class("error-text")
        self.error_label.set_visible(False)
        content.append(self.error_label)

        # Escape key controller
        key_ctl = Gtk.EventControllerKey()
        key_ctl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctl)

        self.set_child(content)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _on_save_clicked(self, _btn):
        title = self.title_entry.get_text().strip()
        if not title:
            self.error_label.set_text("Please enter a habit title.")
            self.error_label.set_visible(True)
            self.title_entry.grab_focus()
            return

        buf = self.desc_view.get_buffer()
        desc = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True).strip()

        if self.on_save:
            self.on_save(title, desc)
        self.close()


class ConfirmDeleteDialog(Gtk.Window):
    """Confirmation modal dialog for destructive actions."""

    def __init__(self, parent, message, on_confirm=None):
        super().__init__(
            title="Confirm Delete",
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
            default_width=380,
            default_height=200,
        )
        self.on_confirm = on_confirm

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_start(24)
        box.set_margin_end(24)
        box.set_margin_top(20)
        box.set_margin_bottom(20)

        icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        icon.set_pixel_size(44)
        box.append(icon)

        msg_label = Gtk.Label(label=message, wrap=True, justify=Gtk.Justification.CENTER)
        box.append(msg_label)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        btn_box.append(cancel_btn)

        del_btn = Gtk.Button(label="Delete")
        del_btn.add_css_class("destructive-action")

        def _do_confirm(_):
            if self.on_confirm:
                self.on_confirm()
            self.close()

        del_btn.connect("clicked", _do_confirm)
        btn_box.append(del_btn)

        box.append(btn_box)

        key_ctl = Gtk.EventControllerKey()
        key_ctl.connect("key-pressed", lambda c, k, code, s: (self.close(), True)[1] if k == Gdk.KEY_Escape else False)
        self.add_controller(key_ctl)

        self.set_child(box)


class HabitRow(Gtk.ListBoxRow):
    """Custom row for the habits list sidebar."""

    def __init__(self, habit, is_completed_today, streak, on_toggle_today):
        super().__init__()
        self.habit = habit
        self.habit_id = habit[0]
        self.habit_title = habit[1]
        self.habit_desc = habit[2] or ""
        self.is_completed_today = is_completed_today
        self.streak = streak
        self.on_toggle_today = on_toggle_today

        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row_box.add_css_class("habit-row")
        row_box.set_margin_start(8)
        row_box.set_margin_end(8)
        row_box.set_margin_top(6)
        row_box.set_margin_bottom(6)

        # Quick Toggle Button
        self.toggle_btn = Gtk.Button()
        self.toggle_btn.set_focusable(False)
        self.toggle_btn.set_valign(Gtk.Align.CENTER)
        self.toggle_btn.add_css_class("circular")
        self.toggle_btn.add_css_class("row-check-btn")

        if is_completed_today:
            self.toggle_btn.set_icon_name("emblem-ok-symbolic")
            self.toggle_btn.add_css_class("checked")
            self.toggle_btn.set_tooltip_text("Completed today! Click to mark incomplete")
        else:
            self.toggle_btn.set_icon_name("media-record-symbolic")
            self.toggle_btn.add_css_class("unchecked")
            self.toggle_btn.set_tooltip_text("Click to mark completed for today")

        self.toggle_btn.connect("clicked", self._on_btn_clicked)
        row_box.append(self.toggle_btn)

        # Title & Description Box
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)
        text_box.set_valign(Gtk.Align.CENTER)

        title_lbl = Gtk.Label(label=self.habit_title, xalign=0.0)
        title_lbl.add_css_class("habit-title")
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        text_box.append(title_lbl)

        if self.habit_desc:
            desc_lbl = Gtk.Label(label=self.habit_desc, xalign=0.0)
            desc_lbl.add_css_class("dim-label")
            desc_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            text_box.append(desc_lbl)

        row_box.append(text_box)

        # Streak pill
        if streak > 0:
            streak_lbl = Gtk.Label(label=f"🔥 {streak}")
            streak_lbl.add_css_class("streak-badge")
            streak_lbl.set_valign(Gtk.Align.CENTER)
            row_box.append(streak_lbl)

        self.set_child(row_box)

    def _on_btn_clicked(self, _btn):
        if self.on_toggle_today:
            self.on_toggle_today(self.habit_id, not self.is_completed_today)


class HabitWindow(Gtk.ApplicationWindow):
    """Main window for GoogleHabit."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("GoogleHabit")
        self.set_default_size(980, 700)

        # Repositories
        self.habits_repo = Habits()
        self.logs_repo = Logs()

        # State
        self.selected_habit_id = None
        self.search_query = ""
        self.current_filter = "all"  # "all", "todo", "done"

        # Build UI
        self._build_header_bar()
        self._build_main_layout()

        # Initial data load
        self.refresh_habits_list()

    def _build_header_bar(self):
        header = Gtk.HeaderBar()
        self.set_titlebar(header)

        # Window Title & Subtitle Widget
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title_box.set_valign(Gtk.Align.CENTER)
        app_title = Gtk.Label(label="GoogleHabit")
        app_title.add_css_class("app-header-title")
        app_sub = Gtk.Label(label="Habit Tracker")
        app_sub.add_css_class("dim-label")
        title_box.append(app_title)
        title_box.append(app_sub)
        header.set_title_widget(title_box)

        # "New Habit" Button
        new_btn = Gtk.Button()
        new_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        new_btn_box.append(Gtk.Image.new_from_icon_name("list-add-symbolic"))
        new_btn_box.append(Gtk.Label(label="New Habit"))
        new_btn.set_child(new_btn_box)
        new_btn.add_css_class("suggested-action")
        new_btn.connect("clicked", lambda b: self.open_add_habit_dialog())
        header.pack_start(new_btn)

        # Refresh Button
        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh all habits")
        refresh_btn.connect("clicked", lambda b: self.refresh_habits_list())
        header.pack_end(refresh_btn)

    def _build_main_layout(self):
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(340)
        paned.set_wide_handle(True)

        # === LEFT PANE: Sidebar ===
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        left_box.add_css_class("sidebar-container")
        left_box.set_size_request(280, -1)

        # Search Bar
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search habits...")
        self.search_entry.connect("search-changed", self._on_search_changed)
        left_box.append(self.search_entry)

        # Filter Segmented Buttons (All / To Do / Done)
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        filter_box.add_css_class("linked")
        filter_box.set_homogeneous(True)

        self.btn_filter_all = Gtk.Button(label="All")
        self.btn_filter_todo = Gtk.Button(label="To Do")
        self.btn_filter_done = Gtk.Button(label="Done")

        self.btn_filter_all.add_css_class("filter-btn-active")
        self.btn_filter_all.connect("clicked", lambda b: self._set_filter("all"))
        self.btn_filter_todo.connect("clicked", lambda b: self._set_filter("todo"))
        self.btn_filter_done.connect("clicked", lambda b: self._set_filter("done"))

        filter_box.append(self.btn_filter_all)
        filter_box.append(self.btn_filter_todo)
        filter_box.append(self.btn_filter_done)
        left_box.append(filter_box)

        # Habits Scrolled List
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self.habit_list_box = Gtk.ListBox()
        self.habit_list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.habit_list_box.add_css_class("navigation-sidebar")
        self.habit_list_box.connect("row-selected", self._on_habit_selected)

        # Placeholder when empty
        placeholder_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        placeholder_box.set_valign(Gtk.Align.CENTER)
        placeholder_box.set_halign(Gtk.Align.CENTER)
        placeholder_box.set_margin_top(40)
        placeholder_box.set_margin_bottom(40)
        p_icon = Gtk.Image.new_from_icon_name("emblem-default-symbolic")
        p_icon.set_pixel_size(36)
        placeholder_box.append(p_icon)
        p_label = Gtk.Label(label="No habits found", wrap=True)
        p_label.add_css_class("dim-label")
        placeholder_box.append(p_label)
        self.habit_list_box.set_placeholder(placeholder_box)

        scrolled.set_child(self.habit_list_box)
        left_box.append(scrolled)

        paned.set_start_child(left_box)

        # === RIGHT PANE: Habit Detail ===
        self.right_scrolled = Gtk.ScrolledWindow()
        self.right_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.right_scrolled.set_hexpand(True)
        self.right_scrolled.set_vexpand(True)

        self.detail_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.detail_container.add_css_class("detail-container")
        self.right_scrolled.set_child(self.detail_container)

        paned.set_end_child(self.right_scrolled)

        self.set_child(paned)

    def _set_filter(self, filter_name):
        self.current_filter = filter_name
        self.btn_filter_all.remove_css_class("filter-btn-active")
        self.btn_filter_todo.remove_css_class("filter-btn-active")
        self.btn_filter_done.remove_css_class("filter-btn-active")

        if filter_name == "all":
            self.btn_filter_all.add_css_class("filter-btn-active")
        elif filter_name == "todo":
            self.btn_filter_todo.add_css_class("filter-btn-active")
        elif filter_name == "done":
            self.btn_filter_done.add_css_class("filter-btn-active")

        self.refresh_habits_list()

    def _on_search_changed(self, entry):
        self.search_query = entry.get_text().strip().lower()
        self.refresh_habits_list()

    def refresh_habits_list(self):
        """Reload habits from database, apply filters, and populate sidebar list."""
        all_habits = self.habits_repo.select(())
        today = date.today()

        # Gather processed items
        filtered_items = []
        for h in all_habits:
            habit_id = h[0]
            title = h[1] or ""
            desc = h[2] or ""

            # Check search query
            if self.search_query:
                if self.search_query not in title.lower() and self.search_query not in desc.lower():
                    continue

            # Check logs & streaks
            logs = self.logs_repo.select((habit_id,))
            dates = [l[1] for l in logs]
            curr_streak, longest_streak, is_today_done = calculate_streaks(dates, today)

            # Check filter
            if self.current_filter == "todo" and is_today_done:
                continue
            if self.current_filter == "done" and not is_today_done:
                continue

            filtered_items.append((h, is_today_done, curr_streak))

        # Clear current listbox rows
        while True:
            row = self.habit_list_box.get_row_at_index(0)
            if row is None:
                break
            self.habit_list_box.remove(row)

        # Repopulate list
        row_to_select = None
        for habit, is_today_done, streak in filtered_items:
            row = HabitRow(
                habit=habit,
                is_completed_today=is_today_done,
                streak=streak,
                on_toggle_today=self.toggle_today_completion,
            )
            self.habit_list_box.append(row)
            if self.selected_habit_id is not None and habit[0] == self.selected_habit_id:
                row_to_select = row

        if row_to_select:
            self.habit_list_box.select_row(row_to_select)
        elif filtered_items:
            first_row = self.habit_list_box.get_row_at_index(0)
            self.habit_list_box.select_row(first_row)
        else:
            self.selected_habit_id = None
            self.show_empty_detail(has_any_habits=bool(all_habits))

    def _on_habit_selected(self, _listbox, row):
        if row is None:
            return
        self.selected_habit_id = row.habit_id
        self.show_habit_detail(self.selected_habit_id)

    def show_empty_detail(self, has_any_habits=False):
        """Displays empty state when no habit is selected or exists."""
        self._clear_detail_container()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        box.set_vexpand(True)
        box.set_hexpand(True)

        icon = Gtk.Image.new_from_icon_name("starred-symbolic")
        icon.set_pixel_size(64)
        box.append(icon)

        if not has_any_habits:
            heading = Gtk.Label(label="No Habits Yet")
            heading.add_css_class("title-1")
            box.append(heading)

            desc = Gtk.Label(
                label="Start building consistency by adding your first daily habit!",
                wrap=True,
                justify=Gtk.Justification.CENTER
            )
            desc.add_css_class("dim-label")
            box.append(desc)

            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            btn_box.set_halign(Gtk.Align.CENTER)

            create_btn = Gtk.Button(label="+ Create First Habit")
            create_btn.add_css_class("suggested-action")
            create_btn.connect("clicked", lambda b: self.open_add_habit_dialog())
            btn_box.append(create_btn)

            sample_btn = Gtk.Button(label="Load Sample Habits")
            sample_btn.connect("clicked", lambda b: self.load_sample_habits())
            btn_box.append(sample_btn)

            box.append(btn_box)
        else:
            heading = Gtk.Label(label="Select a Habit")
            heading.add_css_class("title-1")
            box.append(heading)

            desc = Gtk.Label(
                label="Select a habit from the sidebar to inspect its history, streaks, and log completions.",
                wrap=True,
                justify=Gtk.Justification.CENTER
            )
            desc.add_css_class("dim-label")
            box.append(desc)

        self.detail_container.append(box)

    def show_habit_detail(self, habit_id):
        """Renders comprehensive detail and tracker controls for the selected habit."""
        self._clear_detail_container()

        # Query habit
        rows = self.habits_repo.select_one((habit_id,))
        if not rows:
            self.show_empty_detail(has_any_habits=True)
            return

        habit = rows[0]
        title = habit[1]
        desc = habit[2] or ""

        # Query logs
        logs = self.logs_repo.select((habit_id,))
        date_strings = [l[1] for l in logs]
        today = date.today()
        today_iso = today.isoformat()

        curr_streak, longest_streak, is_today_done = calculate_streaks(date_strings, today)
        total_logs = len(logs)
        last_logged_str = date_strings[0] if date_strings else "None yet"

        # 1. Header Section (Title + Description + Edit/Delete actions)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)

        title_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_col.set_hexpand(True)

        title_label = Gtk.Label(label=title, xalign=0.0)
        title_label.add_css_class("title-1")
        title_label.set_wrap(True)
        title_col.append(title_label)

        if desc:
            desc_label = Gtk.Label(label=desc, xalign=0.0)
            desc_label.add_css_class("dim-label")
            desc_label.set_wrap(True)
            title_col.append(desc_label)

        header_box.append(title_col)

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_valign(Gtk.Align.START)

        edit_btn = Gtk.Button()
        edit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        edit_box.append(Gtk.Image.new_from_icon_name("document-edit-symbolic"))
        edit_box.append(Gtk.Label(label="Edit"))
        edit_btn.set_child(edit_box)
        edit_btn.connect("clicked", lambda b: self.open_edit_habit_dialog(habit))
        btn_box.append(edit_btn)

        del_btn = Gtk.Button()
        del_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        del_box.append(Gtk.Image.new_from_icon_name("edit-delete-symbolic"))
        del_box.append(Gtk.Label(label="Delete"))
        del_btn.set_child(del_box)
        del_btn.add_css_class("destructive-action")
        del_btn.connect("clicked", lambda b: self.confirm_delete_habit(habit))
        btn_box.append(del_btn)

        header_box.append(btn_box)
        self.detail_container.append(header_box)

        # 2. Today's Status Banner Card
        today_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        today_card.add_css_class("card")
        if is_today_done:
            today_card.add_css_class("today-card-done")
        else:
            today_card.add_css_class("today-card-pending")

        today_icon = Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if is_today_done else "appointment-new-symbolic"
        )
        today_icon.set_pixel_size(36)
        today_card.append(today_icon)

        today_text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        today_text_box.set_hexpand(True)
        today_text_box.set_valign(Gtk.Align.CENTER)

        if is_today_done:
            status_title = Gtk.Label(label="Completed for Today! 🎉", xalign=0.0)
            status_title.add_css_class("today-status-title")
            status_desc = Gtk.Label(
                label=f"Current streak: {curr_streak} day{'s' if curr_streak != 1 else ''}. Keep the momentum going!",
                xalign=0.0
            )
            status_desc.add_css_class("dim-label")
        else:
            status_title = Gtk.Label(label="Not Completed Today Yet", xalign=0.0)
            status_title.add_css_class("today-status-title")
            status_desc = Gtk.Label(label="Check in today to maintain or start your streak.", xalign=0.0)
            status_desc.add_css_class("dim-label")

        today_text_box.append(status_title)
        today_text_box.append(status_desc)
        today_card.append(today_text_box)

        today_action_btn = Gtk.Button()
        today_action_btn.set_valign(Gtk.Align.CENTER)
        if is_today_done:
            today_action_btn.set_label("Undo Today")
            today_action_btn.add_css_class("flat")
            today_action_btn.connect("clicked", lambda b: self.toggle_today_completion(habit_id, False))
        else:
            today_action_btn.set_label("✓ Mark Completed")
            today_action_btn.add_css_class("suggested-action")
            today_action_btn.connect("clicked", lambda b: self.toggle_today_completion(habit_id, True))

        today_card.append(today_action_btn)
        self.detail_container.append(today_card)

        # 3. Stats Overview Grid (4 Cards)
        stats_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        stats_box.set_homogeneous(True)

        def make_stat_tile(icon_name, value_text, label_text, badge_class=None):
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card.add_css_class("stat-card")
            card.set_margin_top(4)
            card.set_margin_bottom(4)

            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            ico = Gtk.Image.new_from_icon_name(icon_name)
            lbl = Gtk.Label(label=label_text, xalign=0.0)
            lbl.add_css_class("stat-title")
            top.append(ico)
            top.append(lbl)
            card.append(top)

            val = Gtk.Label(label=value_text, xalign=0.0)
            val.add_css_class("stat-value")
            if badge_class:
                val.add_css_class(badge_class)
            card.append(val)
            return card

        stats_box.append(make_stat_tile("starred-symbolic", f"{curr_streak} d", "Current Streak"))
        stats_box.append(make_stat_tile("trophy-gold-symbolic", f"{longest_streak} d", "Best Streak"))
        stats_box.append(make_stat_tile("emblem-ok-symbolic", str(total_logs), "Total Check-ins"))
        stats_box.append(make_stat_tile("x-office-calendar-symbolic", last_logged_str, "Last Completed"))

        self.detail_container.append(stats_box)

        # 4. Interactive Last 7 Days Strip
        strip_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        strip_title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        strip_title = Gtk.Label(label="Last 7 Days Activity", xalign=0.0)
        strip_title.add_css_class("section-title")
        strip_hint = Gtk.Label(label="(click any day to toggle check-in)", xalign=0.0)
        strip_hint.add_css_class("dim-label")
        strip_title_box.append(strip_title)
        strip_title_box.append(strip_hint)
        strip_section.append(strip_title_box)

        days_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        days_box.set_homogeneous(True)

        logged_set = set(date_strings)
        for i in range(6, -1, -1):
            day_target = today - timedelta(days=i)
            day_iso = day_target.isoformat()
            is_done = day_iso in logged_set
            is_current = (day_target == today)

            day_btn = Gtk.Button()
            day_btn.set_focusable(False)
            day_btn.add_css_class("day-bubble")
            if is_done:
                day_btn.add_css_class("active-day")
            if is_current:
                day_btn.add_css_class("today-bubble")

            inner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            inner_box.set_halign(Gtk.Align.CENTER)

            day_name = day_target.strftime("%a")
            day_num = day_target.strftime("%d")

            d_name_lbl = Gtk.Label(label=day_name)
            d_name_lbl.add_css_class("day-name-label")
            inner_box.append(d_name_lbl)

            d_num_lbl = Gtk.Label(label=day_num)
            d_num_lbl.add_css_class("day-num-label")
            inner_box.append(d_num_lbl)

            status_icon_name = "emblem-ok-symbolic" if is_done else "media-record-symbolic"
            status_ico = Gtk.Image.new_from_icon_name(status_icon_name)
            status_ico.set_pixel_size(14)
            inner_box.append(status_ico)

            day_btn.set_child(inner_box)
            day_btn.set_tooltip_text(f"{day_target.strftime('%A, %b %d')} - {'Completed' if is_done else 'Not completed'}")

            # Clicking toggles this specific date
            def make_toggle_handler(h_id, d_str, currently_done):
                return lambda b: self.toggle_date_completion(h_id, d_str, not currently_done)

            day_btn.connect("clicked", make_toggle_handler(habit_id, day_iso, is_done))
            days_box.append(day_btn)

        strip_section.append(days_box)
        self.detail_container.append(strip_section)

        # 5. Log Custom Date Row
        manual_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        manual_box.set_margin_top(4)

        manual_label = Gtk.Label(label="Log past date:", xalign=0.0)
        manual_label.add_css_class("form-label")
        manual_box.append(manual_label)

        date_entry = Gtk.Entry()
        date_entry.set_placeholder_text("YYYY-MM-DD")
        date_entry.set_text(today_iso)
        date_entry.set_width_chars(12)
        manual_box.append(date_entry)

        log_btn = Gtk.Button(label="+ Record Log")
        log_btn.connect("clicked", lambda b: self._on_manual_log(habit_id, date_entry.get_text().strip()))
        manual_box.append(log_btn)

        self.detail_container.append(manual_box)

        # 6. Completion History List
        history_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        hist_title = Gtk.Label(label=f"Completion History ({total_logs})", xalign=0.0)
        hist_title.add_css_class("section-title")
        history_section.append(hist_title)

        if not logs:
            no_logs = Gtk.Label(label="No check-ins recorded yet.", xalign=0.0)
            no_logs.add_css_class("dim-label")
            history_section.append(no_logs)
        else:
            hist_list_box = Gtk.ListBox()
            hist_list_box.add_css_class("boxed-list")
            hist_list_box.set_selection_mode(Gtk.SelectionMode.NONE)

            for log_row in logs:
                log_id, log_date_str, _ = log_row
                formatted_d, rel_d = format_relative_date(log_date_str, today)

                h_row = Gtk.ListBoxRow()
                h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                h_box.set_margin_start(12)
                h_box.set_margin_end(12)
                h_box.set_margin_top(8)
                h_box.set_margin_bottom(8)

                ico = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                h_box.append(ico)

                date_lbl = Gtk.Label(label=formatted_d, xalign=0.0)
                date_lbl.set_hexpand(True)
                h_box.append(date_lbl)

                if rel_d:
                    rel_lbl = Gtk.Label(label=rel_d)
                    rel_lbl.add_css_class("dim-label")
                    h_box.append(rel_lbl)

                # Delete single log button
                del_log_btn = Gtk.Button.new_from_icon_name("edit-delete-symbolic")
                del_log_btn.set_focusable(False)
                del_log_btn.add_css_class("flat")
                del_log_btn.set_tooltip_text(f"Delete log for {log_date_str}")

                def make_del_log_handler(l_id, h_id):
                    return lambda b: self.delete_log_entry(l_id, h_id)

                del_log_btn.connect("clicked", make_del_log_handler(log_id, habit_id))
                h_box.append(del_log_btn)

                h_row.set_child(h_box)
                hist_list_box.append(h_row)

            history_section.append(hist_list_box)

        self.detail_container.append(history_section)

    def _clear_detail_container(self):
        while True:
            child = self.detail_container.get_first_child()
            if child is None:
                break
            self.detail_container.remove(child)

    def toggle_today_completion(self, habit_id, mark_completed):
        """Toggle today's check-in for a given habit."""
        today_str = date.today().isoformat()
        self.toggle_date_completion(habit_id, today_str, mark_completed)

    def toggle_date_completion(self, habit_id, date_str, mark_completed):
        """Toggle check-in for a specific date."""
        if mark_completed:
            # Check if already present
            existing = self.logs_repo.find_by_habit_and_date(habit_id, date_str)
            if not existing:
                self.logs_repo.insert((date_str, habit_id))
        else:
            self.logs_repo.delete_by_habit_and_date(habit_id, date_str)

        self.refresh_habits_list()

    def _on_manual_log(self, habit_id, date_text):
        """Validates and records a completion for a typed date."""
        try:
            parsed = date.fromisoformat(date_text)
            date_iso = parsed.isoformat()
        except ValueError:
            # Invalid date format
            dlg = Gtk.Window(title="Invalid Date", transient_for=self, modal=True)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            box.set_margin_start(20)
            box.set_margin_end(20)
            box.set_margin_top(16)
            box.set_margin_bottom(16)
            box.append(Gtk.Label(label="Please enter date in YYYY-MM-DD format (e.g. 2026-10-17)"))
            ok_btn = Gtk.Button(label="OK")
            ok_btn.connect("clicked", lambda b: dlg.close())
            box.append(ok_btn)
            dlg.set_child(box)
            dlg.present()
            return

        self.toggle_date_completion(habit_id, date_iso, True)

    def delete_log_entry(self, log_id, habit_id):
        """Deletes a specific log record by its log_id."""
        self.logs_repo.delete((log_id,))
        self.refresh_habits_list()

    def open_add_habit_dialog(self):
        """Opens dialog to create a new habit."""
        def on_save(title, desc):
            self.habits_repo.insert((title, desc))
            # Retrieve newly inserted habit id to select it
            all_habits = self.habits_repo.select(())
            if all_habits:
                # Find matching habit
                for h in reversed(all_habits):
                    if h[1] == title:
                        self.selected_habit_id = h[0]
                        break
            self.refresh_habits_list()

        dlg = HabitEditDialog(self, habit=None, on_save=on_save)
        dlg.present()

    def open_edit_habit_dialog(self, habit):
        """Opens dialog to edit habit title and description."""
        habit_id = habit[0]

        def on_save(new_title, new_desc):
            self.habits_repo.update((new_title, new_desc, habit_id))
            self.refresh_habits_list()

        dlg = HabitEditDialog(self, habit=habit, on_save=on_save)
        dlg.present()

    def confirm_delete_habit(self, habit):
        """Asks for confirmation before deleting a habit and its logs."""
        habit_id = habit[0]
        habit_title = habit[1]

        def on_confirm():
            self.logs_repo.delete_by_habit(habit_id)
            self.habits_repo.delete((habit_id,))
            self.selected_habit_id = None
            self.refresh_habits_list()

        msg = f"Are you sure you want to delete '{habit_title}'?\nAll log history for this habit will also be removed."
        dlg = ConfirmDeleteDialog(self, message=msg, on_confirm=on_confirm)
        dlg.present()

    def load_sample_habits(self):
        """Adds starter sample habits with simulated completion streaks."""
        today = date.today()
        samples = [
            ("Drink 2L Water", "Drink 8 glasses of water throughout the day", 4),
            ("Morning Exercise", "30 minutes workout, yoga, or stretching", 2),
            ("Daily Reading", "Read at least 15 pages of a book", 5),
            ("Evening Meditation", "10 minutes mindful breathing before bed", 0),
        ]
        for title, desc, streak_days in samples:
            self.habits_repo.insert((title, desc))
            # Find the inserted habit
            for h in self.habits_repo.select(()):
                if h[1] == title:
                    h_id = h[0]
                    # Create past logs for streak
                    for d in range(streak_days):
                        past_date = (today - timedelta(days=d)).isoformat()
                        self.logs_repo.insert((past_date, h_id))
                    break

        self.refresh_habits_list()


class HabitApplication(Gtk.Application):
    """GTK4 Application wrapper for GoogleHabit."""

    def __init__(self):
        super().__init__(
            application_id="org.googlehabit.app",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )

    def do_activate(self):
        self._load_css()
        win = self.props.active_window
        if not win:
            win = HabitWindow(application=self)
        win.present()

    def _load_css(self):
        css_data = """
        .app-header-title {
            font-size: 1.05rem;
            font-weight: 800;
        }
        .sidebar-container {
            padding: 12px;
            background-color: alpha(currentColor, 0.02);
            border-right: 1px solid alpha(currentColor, 0.08);
        }
        .detail-container {
            padding: 24px 32px;
        }
        .habit-row {
            padding: 8px 10px;
            border-radius: 8px;
        }
        .habit-title {
            font-weight: 700;
            font-size: 0.98rem;
        }
        .row-check-btn {
            min-width: 32px;
            min-height: 32px;
            padding: 0;
            border-radius: 9999px;
        }
        .row-check-btn.checked {
            background-color: #2ec27e;
            color: white;
            border: none;
        }
        .row-check-btn.unchecked {
            background-color: alpha(currentColor, 0.06);
            color: alpha(currentColor, 0.4);
            border: 1px solid alpha(currentColor, 0.15);
        }
        .filter-btn-active {
            background-color: alpha(#3584e4, 0.2);
            color: #3584e4;
            font-weight: bold;
        }
        .card {
            border-radius: 12px;
            padding: 16px;
        }
        .today-card-done {
            background-color: alpha(#2ec27e, 0.12);
            border: 1px solid alpha(#2ec27e, 0.4);
        }
        .today-card-pending {
            background-color: alpha(#3584e4, 0.08);
            border: 1px solid alpha(#3584e4, 0.28);
        }
        .today-status-title {
            font-size: 1.15rem;
            font-weight: 700;
        }
        .stat-card {
            background-color: alpha(currentColor, 0.04);
            border: 1px solid alpha(currentColor, 0.09);
            border-radius: 10px;
            padding: 12px 14px;
        }
        .stat-title {
            font-size: 0.8rem;
            opacity: 0.72;
            font-weight: 600;
        }
        .stat-value {
            font-size: 1.45rem;
            font-weight: 800;
        }
        .streak-badge {
            background-color: #ff7800;
            color: white;
            border-radius: 9999px;
            padding: 2px 8px;
            font-size: 0.78rem;
            font-weight: 800;
        }
        .day-bubble {
            border-radius: 10px;
            padding: 6px 4px;
            min-width: 48px;
            border: 1px solid alpha(currentColor, 0.12);
            background-color: alpha(currentColor, 0.03);
        }
        .day-bubble.active-day {
            background-color: #2ec27e;
            color: white;
            border-color: #2ec27e;
        }
        .day-bubble.today-bubble {
            border: 2px solid #3584e4;
        }
        .day-name-label {
            font-size: 0.75rem;
            font-weight: 600;
            opacity: 0.85;
        }
        .day-num-label {
            font-size: 0.95rem;
            font-weight: 800;
        }
        .section-title {
            font-size: 1.05rem;
            font-weight: 700;
        }
        .form-label {
            font-weight: 600;
            font-size: 0.92rem;
        }
        .error-text {
            color: #e01b24;
            font-size: 0.85rem;
        }
        .title-1 {
            font-size: 1.6rem;
            font-weight: 800;
        }
        .title-2 {
            font-size: 1.2rem;
            font-weight: 700;
        }
        .dim-label {
            opacity: 0.65;
            font-size: 0.88rem;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_string(css_data)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )


def main():
    app = HabitApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
