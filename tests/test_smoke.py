from types import SimpleNamespace

from handlers.admin import (
    admin_states,
    admin_uploading,
    handle_admin_photo,
    is_admin_uploading,
    list_discounts,
    list_products,
    show_admin_panel,
    show_all_users,
    show_category_report,
    show_daily_report,
    show_low_stock,
    show_orders_by_status,
    show_sales_report,
    show_top_products,
    start_add_discount,
    start_add_product,
    start_broadcast,
    start_delete_product,
    start_edit_product,
    start_find_user,
)


def _fake_db():
    return SimpleNamespace(
        get_user_count=lambda: 1,
        get_product_count=lambda: 3,
        get_order_stats=lambda: {"summary": {"total_orders": 2, "total_revenue": 100.0}},
        get_daily_stats=lambda: {"new_orders": 1},
        get_all_users=lambda: [{"user_id": 1, "first_name": "Jane"}],
        get_active_users=lambda days=7: [{"user_id": 1, "first_name": "Jane"}],
        get_products=lambda **kwargs: [{"id": 1, "name_am": "ምርት", "price": 10.0}],
        get_order_items=lambda order_id: [],
        get_sales_report=lambda days=30: [{"sale_date": "2026-09-01", "total_sales": 100.0}],
        get_top_products=lambda limit=10: [{"id": 1, "name_am": "ምርት", "total_sold": 3}],
        get_category_stats=lambda: [{"category": "Men", "product_count": 2}],
        get_low_stock_products=lambda threshold=5: [{"id": 1, "name_am": "ምርት", "stock_quantity": 2}],
    )


def _fake_bot():
    class FakeBot:
        def send_message(self, *args, **kwargs):
            return True

        def reply_to(self, *args, **kwargs):
            return True

    return FakeBot()


def test_admin_placeholder_functions_return_non_none():
    db = _fake_db()
    bot = _fake_bot()
    message = SimpleNamespace(chat=SimpleNamespace(id=1), from_user=SimpleNamespace(id=123))

    assert show_orders_by_status(message, None, db, bot) is not None
    assert show_all_users(message, db, bot) is not None
    assert start_find_user(message, db, bot) is not None
    assert start_broadcast(message, db, bot) is not None
    assert show_sales_report(message, db, bot) is not None
    assert show_top_products(message, db, bot) is not None
    assert show_daily_report(message, db, bot) is not None
    assert show_category_report(message, db, bot) is not None
    assert start_add_discount(message, db, bot) is not None
    assert list_discounts(message, db, bot) is not None
    assert list_products(message, db, bot) is not None
    assert start_edit_product(message, db, bot) is not None
    assert start_delete_product(message, db, bot) is not None
    assert show_low_stock(message, db, bot) is not None
    assert show_admin_panel(message) is not None


def test_start_add_product_registers_next_step_on_prompt_message():
    db = _fake_db()

    class FakeBot:
        def __init__(self):
            self.sent_messages = []
            self.registered = []

        def send_message(self, chat_id, text, **kwargs):
            msg = SimpleNamespace(chat=SimpleNamespace(id=chat_id), from_user=SimpleNamespace(id=123), text=text)
            self.sent_messages.append(msg)
            return msg

        def register_next_step_handler(self, message, callback, *args, **kwargs):
            self.registered.append((message, callback, args, kwargs))

    bot = FakeBot()
    original = SimpleNamespace(chat=SimpleNamespace(id=1), from_user=SimpleNamespace(id=123), text='trigger')

    start_add_product(original, db, bot)

    assert len(bot.sent_messages) == 1
    assert len(bot.registered) == 1
    assert bot.registered[0][0] is bot.sent_messages[0]


def test_admin_photo_upload_helpers_handle_add_product_state():
    user_id = 101
    admin_states.clear()
    admin_uploading.clear()
    admin_states[user_id] = {'action': 'add_product', 'step': 7, 'data': {'name_am': 'ምርት', 'name_en': 'Product', 'price': 100, 'size': 'M', 'category': 'Men', 'stock_quantity': 5}}
    admin_uploading.add(user_id)

    assert is_admin_uploading(user_id) is True

    class FakeBot:
        def __init__(self):
            self.messages = []

        def send_message(self, chat_id, text, **kwargs):
            self.messages.append((chat_id, text, kwargs))
            return True

    bot = FakeBot()
    msg = SimpleNamespace(
        chat=SimpleNamespace(id=123),
        from_user=SimpleNamespace(id=user_id),
        photo=[SimpleNamespace(file_id='abc')],
        content_type='photo',
    )

    class FakeDB:
        def create_product(self, product_data):
            return 42

        def log_activity(self, *args, **kwargs):
            return True

    db = FakeDB()
    assert handle_admin_photo(msg, db, bot) is True
    assert admin_states.get(user_id) is None
