from django.core.management.base import BaseCommand
from api.models import BrowsingMemoCount, DmLearningEfficiency, Note, MemoCategory, Purpose, Memo, User
import math
from django.db.models import Max
import datetime


now = datetime.datetime.now(datetime.timezone.utc)
today = datetime.datetime.now(datetime.timezone.utc).date()


#DmLearningEfficiencyにデータを追加する際、外部キーはモデルインスタンスである必要があるため、全モデルデータを取得
notes = Note.objects.filter(is_active=True)
parent_memo_categories = MemoCategory.objects.filter(is_active=True, parent_memo_category__isnull=True)
child_memo_categories = MemoCategory.objects.filter(is_active=True, parent_memo_category__isnull=False)
purposes = Purpose.objects.filter(is_active=True)
memos = Memo.objects.filter(is_active=True)
users = User.objects.filter(is_active=True)


def calculate_learning_efficiency(latest_browsing_datetime):
    subtract_datetime = now - latest_browsing_datetime
    elapsed_minutes = math.ceil(subtract_datetime.total_seconds() / 60)
    learning_efficiency = round(100 * (1.84 / ((math.log10(elapsed_minutes) ** 1.25) + 1.84)),1)
    
    return learning_efficiency


def create_learning_efficiency_record(latest_browsing_memo):
    return DmLearningEfficiency(
        aggregate_date=today,
        learning_efficiency_rate=calculate_learning_efficiency(latest_browsing_memo["max_datetime"]),
        note=notes.get(pk=latest_browsing_memo["memo__note"]),
        parent_memo_category=parent_memo_categories.get(pk=latest_browsing_memo["memo__parent_memo_category"]),
        child_memo_category=child_memo_categories.get(pk=latest_browsing_memo["memo__child_memo_category"]),
        purpose=purposes.get(pk=latest_browsing_memo["memo__purpose"]),
        memo=memos.get(pk=latest_browsing_memo["memo"]),
        user=users.get(pk=latest_browsing_memo["user"])
    )


def update_learning_efficiency_record(latest_browsing_memo, max_browsing_datetime_all_date):
    return DmLearningEfficiency(
        pk=DmLearningEfficiency.objects.get(
            aggregate_date=max_browsing_datetime_all_date,
            memo__note_id=latest_browsing_memo["memo__note"],
            memo__parent_memo_category_id=latest_browsing_memo["memo__parent_memo_category"],
            memo__child_memo_category_id=latest_browsing_memo["memo__child_memo_category"],
            memo__purpose_id=latest_browsing_memo["memo__purpose"],
            memo__memo_id=latest_browsing_memo["memo"], 
            user__user_id=latest_browsing_memo["user"]
            ).id,
        learning_efficiency_rate=calculate_learning_efficiency(latest_browsing_memo["max_datetime"]),
        note=notes.get(pk=latest_browsing_memo["memo__note"]),
        parent_memo_category=parent_memo_categories.get(pk=latest_browsing_memo["memo__parent_memo_category"]),
        child_memo_category=child_memo_categories.get(pk=latest_browsing_memo["memo__child_memo_category"]),
        purpose=purposes.get(pk=latest_browsing_memo["memo__purpose"]),
        memo=memos.get(pk=latest_browsing_memo["memo"]),
        user=users.get(pk=latest_browsing_memo["user"])
    )


class Command(BaseCommand):
    def handle(self, *args, **options):
        latest_browsing_memos = BrowsingMemoCount.objects.filter(
            memo__is_active=True,
            memo__note__is_active=True,
            memo__parent_memo_category__is_active=True,
            memo__child_memo_category__is_active=True,
            memo__purpose__is_active=True,
            ).values(
                'memo__note',
                'memo__parent_memo_category',
                'memo__child_memo_category',
                'memo__purpose',
                'memo',
                'user').annotate(max_datetime=Max('updated_at'))

        max_browsing_datetime_all_date = DmLearningEfficiency.objects.aggregate(max_datetime_all=Max("updated_at")).get('max_datetime_all').date()

        learning_efficiencies = []
        if max_browsing_datetime_all_date == today:
            print('update処理を開始')
            for latest_browsing_memo in latest_browsing_memos:
                learning_efficiencies.append(update_learning_efficiency_record(latest_browsing_memo, max_browsing_datetime_all_date))
            DmLearningEfficiency.objects.bulk_update(learning_efficiencies, [
                'learning_efficiency_rate',
                'note',
                'parent_memo_category',
                'child_memo_category',
                'purpose',
                'memo',
                'user'
            ])
            print('update処理を終了')
        else:
            print('insert処理を開始')
            for latest_browsing_memo in latest_browsing_memos:
                learning_efficiencies.append(create_learning_efficiency_record(latest_browsing_memo))
            DmLearningEfficiency.objects.bulk_create(learning_efficiencies)
            print('insert処理を終了')