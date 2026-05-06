from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import (
    Member, ElectionApplication, AttendanceSession,
    AttendanceRecord, Committee, CommitteeMember, Announcement, SiteSettings
)

admin.site.register(SiteSettings)
admin.site.register(Member)
admin.site.register(ElectionApplication)
admin.site.register(AttendanceSession)
admin.site.register(AttendanceRecord)
admin.site.register(Committee)
admin.site.register(CommitteeMember)
admin.site.register(Announcement)

from .models import Meeting, Agenda, AgendaSection, AgendaItem, AgendaSubItem

admin.site.register(Meeting)
admin.site.register(Agenda)
admin.site.register(AgendaSection)
admin.site.register(AgendaItem)
admin.site.register(AgendaSubItem)

from .models import Account, Transaction

admin.site.register(Account)
admin.site.register(Transaction)