
import csv
import io

from sqlalchemy.orm import Session

from ..models import (
    Family,
    Child,
    Lesson,
    Booking,
    Attendance,
    Subscription,
    Payment,
)


def create_csv(rows, headers):
    """
    Создаёт CSV в UTF-8 с BOM,
    чтобы кириллица корректно открывалась в Excel.
    """
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow(headers)

    for row in rows:
        writer.writerow([
            "" if value is None else str(value)
            for value in row
        ])

    return output.getvalue().encode("utf-8-sig")


def export_families(db: Session):
    families = db.query(Family).order_by(Family.id).all()

    rows = [
        (
            family.id,
            family.name,
            family.phone,
            family.created_at,
        )
        for family in families
    ]

    return create_csv(
        rows,
        ["ID семьи", "Название семьи", "Телефон", "Дата создания"]
    )


def export_children(db: Session):
    children = (
        db.query(Child)
        .order_by(Child.id)
        .all()
    )

    rows = [
        (
            child.id,
            child.family_id,
            child.first_name,
            child.last_name,
            child.birth_date,
            child.created_at,
        )
        for child in children
    ]

    return create_csv(
        rows,
        [
            "ID ребёнка",
            "ID семьи",
            "Имя",
            "Фамилия",
            "Дата рождения",
            "Дата добавления",
        ]
    )


def export_lessons(db: Session):
    lessons = db.query(Lesson).order_by(Lesson.starts_at).all()

    rows = [
        (
            lesson.id,
            lesson.title,
            lesson.description,
            lesson.starts_at,
            lesson.duration_minutes,
            lesson.capacity,
            lesson.price,
            lesson.is_active,
        )
        for lesson in lessons
    ]

    return create_csv(
        rows,
        [
            "ID занятия",
            "Название",
            "Описание",
            "Дата и время",
            "Длительность (мин)",
            "Вместимость",
            "Стоимость",
            "Активно",
        ]
    )


def export_bookings(db: Session):
    bookings = (
        db.query(Booking, Child, Lesson)
        .join(Child, Booking.child_id == Child.id)
        .join(Lesson, Booking.lesson_id == Lesson.id)
        .order_by(Booking.created_at.desc())
        .all()
    )

    rows = [
        (
            booking.id,
            child.family_id,
            child.id,
            f"{child.first_name} {child.last_name or ''}".strip(),
            lesson.id,
            lesson.title,
            lesson.starts_at,
            booking.status,
            booking.created_at,
        )
        for booking, child, lesson in bookings
    ]

    return create_csv(
        rows,
        [
            "ID записи",
            "ID семьи",
            "ID ребёнка",
            "Имя ребёнка",
            "ID занятия",
            "Занятие",
            "Дата занятия",
            "Статус записи",
            "Дата записи",
        ]
    )


def export_attendance(db: Session):
    records = (
        db.query(Attendance, Booking, Child, Lesson)
        .join(Booking, Attendance.booking_id == Booking.id)
        .join(Child, Booking.child_id == Child.id)
        .join(Lesson, Booking.lesson_id == Lesson.id)
        .order_by(Attendance.marked_at.desc())
        .all()
    )

    rows = [
        (
            attendance.id,
            booking.id,
            child.family_id,
            f"{child.first_name} {child.last_name or ''}".strip(),
            lesson.title,
            lesson.starts_at,
            attendance.status,
            attendance.marked_at,
        )
        for attendance, booking, child, lesson in records
    ]

    return create_csv(
        rows,
        [
            "ID посещения",
            "ID записи",
            "ID семьи",
            "Ребёнок",
            "Занятие",
            "Дата занятия",
            "Статус посещения",
            "Дата отметки",
        ]
    )


def export_subscriptions(db: Session):
    subscriptions = (
        db.query(Subscription)
        .order_by(Subscription.id)
        .all()
    )

    rows = [
        (
            subscription.id,
            subscription.family_id,
            subscription.child_id,
            subscription.title,
            subscription.total_lessons,
            subscription.used_lessons,
            subscription.total_lessons - subscription.used_lessons,
            subscription.price,
            subscription.expires_at,
            subscription.is_active,
        )
        for subscription in subscriptions
    ]

    return create_csv(
        rows,
        [
            "ID абонемента",
            "ID семьи",
            "ID ребёнка",
            "Название",
            "Всего занятий",
            "Использовано",
            "Осталось",
            "Стоимость",
            "Срок действия",
            "Активен",
        ]
    )


def export_payments(db: Session):
    payments = (
        db.query(Payment)
        .order_by(Payment.created_at.desc())
        .all()
    )

    rows = [
        (
            payment.id,
            payment.family_id,
            payment.subscription_id,
            payment.amount,
            payment.status,
            payment.payment_method,
            payment.credited,
            payment.created_at,
        )
        for payment in payments
    ]

    return create_csv(
        rows,
        [
            "ID платежа",
            "ID семьи",
            "ID абонемента",
            "Сумма",
            "Статус",
            "Способ оплаты",
            "Зачислен",
            "Дата создания",
        ]
    )


EXPORTS = {
    "families": export_families,
    "children": export_children,
    "lessons": export_lessons,
    "bookings": export_bookings,
    "attendance": export_attendance,
    "subscriptions": export_subscriptions,
    "payments": export_payments,
}
