from django.db import models
from django.contrib.auth.hashers import make_password
from django.core.validators import RegexValidator

student_id_validator = RegexValidator(regex=r'^\d{6}$', message="Student ID must be exactly 6 digits.")

class PermissionTier(models.TextChoices):
    APPLICANT = 'APPLICANT', 'Applicant'
    OFFICER   = 'OFFICER',   'Officer'
    SCI       = 'SCI',       'SCI'

class Member(models.Model):
    class Grade(models.TextChoices):
        NINTH    = '9',  '9th Grade'
        TENTH    = '10', '10th Grade'
        ELEVENTH = '11', '11th Grade'
        TWELFTH  = '12', '12th Grade'

    class ShirtSize(models.TextChoices):
        XS  = 'XS',  'XS'
        S   = 'S',   'Small'
        M   = 'M',   'Medium'
        L   = 'L',   'Large'
        XL  = 'XL',  'XL'
        XXL = 'XXL', 'XXL'

    class DuesStatus(models.TextChoices):
        PAID    = 'PAID',    'Paid'
        PENDING = 'PENDING', 'Pending'

    class MemberStatus(models.TextChoices):
        ACTIVE  = 'ACTIVE',  'Active'
        PENDING = 'PENDING', 'Pending'
        ALUMNI  = 'ALUMNI',  'Alumni'

    class ElectedPosition(models.TextChoices):
        NONE      = '',          'No position'
        EXEC_PRES = 'EXEC_PRES', 'Executive President'
        EXEC_VP   = 'EXEC_VP',   'Executive Vice President'
        EXEC_PARL = 'EXEC_PARL', 'Executive Parliamentarian'
        EXEC_SEC  = 'EXEC_SEC',  'Executive Secretary'
        EXEC_TRES = 'EXEC_TRES', 'Executive Treasurer'
        SR_PRES   = 'SR_PRES',   'Senior President'
        SR_VP     = 'SR_VP',     'Senior Vice President'
        SR_SEC    = 'SR_SEC',    'Senior Secretary'
        JR_PRES   = 'JR_PRES',   'Junior President'
        JR_VP     = 'JR_VP',     'Junior Vice President'
        JR_SEC    = 'JR_SEC',    'Junior Secretary'
        SO_PRES   = 'SO_PRES',   'Sophomore President'
        SO_VP     = 'SO_VP',     'Sophomore Vice President'
        SO_SEC    = 'SO_SEC',    'Sophomore Secretary'
        FR_PRES   = 'FR_PRES',   'Freshman President'
        FR_VP     = 'FR_VP',     'Freshman Vice President'
        FR_SEC    = 'FR_SEC',    'Freshman Secretary'

    student_id                   = models.CharField(max_length=6, unique=True, validators=[student_id_validator])
    full_name                    = models.CharField(max_length=120)
    email                        = models.EmailField(blank=True)
    password_hash                = models.CharField(max_length=255, blank=True)
    grade                        = models.CharField(max_length=2, choices=Grade.choices, blank=True)
    shirt_size                   = models.CharField(max_length=3, choices=ShirtSize.choices, blank=True)
    dues_status                  = models.CharField(max_length=10, choices=DuesStatus.choices, default=DuesStatus.PENDING)
    member_status                = models.CharField(max_length=10, choices=MemberStatus.choices, default=MemberStatus.PENDING)
    permission_tier              = models.CharField(max_length=10, choices=PermissionTier.choices, default=PermissionTier.APPLICANT)
    elected_position             = models.CharField(max_length=20, choices=ElectedPosition.choices, default='', blank=True)
    attendance_warning_dismissed = models.BooleanField(default=False)
    created_at                   = models.DateTimeField(auto_now_add=True)
    updated_at                   = models.DateTimeField(auto_now=True)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def unexcused_absences(self):
        return self.attendance_records.filter(status='UNEXCUSED').count()

    def excused_absences(self):
        return self.attendance_records.filter(status='EXCUSED').count()

    def has_attendance_warning(self):
        if self.attendance_warning_dismissed:
            return False
        return self.unexcused_absences() >= 2 or self.excused_absences() >= 4
    
    def unexcused_absences(self):
        return self.attendance_records.filter(status='UNEXCUSED').count()

    def excused_absences(self):
        return self.attendance_records.filter(status='EXCUSED').count()
    
    def present_count(self):
        """Count only sessions where member is marked as PRESENT"""
        return self.attendance_records.filter(status='PRESENT').count()

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"

    class Meta:
        ordering = ['full_name']


class ElectionApplication(models.Model):
    class Position(models.TextChoices):
        PRESIDENT = 'PRESIDENT', 'President'
        EVP       = 'EVP',       'Executive Vice President'
        VP        = 'VP',        'Vice President'
        SECRETARY = 'SECRETARY', 'Secretary'
        TREASURER = 'TREASURER', 'Treasurer'
        HISTORIAN = 'HISTORIAN', 'Historian'
        SERGEANT  = 'SERGEANT',  'Sergeant at Arms'
        REP       = 'REP',       'Class Representative'

    class ApprovalStatus(models.TextChoices):
        PENDING  = 'PENDING',  'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    member            = models.OneToOneField(Member, on_delete=models.CASCADE, related_name='election_application')
    desired_position  = models.CharField(max_length=20, choices=Position.choices)
    interview_slot    = models.DateTimeField(null=True, blank=True)
    approval_status   = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    interview_answers = models.JSONField(default=list)
    e_signature_1     = models.CharField(max_length=120, blank=True)
    e_signature_2     = models.CharField(max_length=120, blank=True)
    e_signature_3     = models.CharField(max_length=120, blank=True)
    submitted_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.full_name} -> {self.desired_position} ({self.approval_status})"

    class Meta:
        ordering = ['-submitted_at']


class AttendanceSession(models.Model):
    session_name = models.CharField(max_length=200)
    created_by   = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name='sessions_created')
    qr_token     = models.CharField(max_length=64, unique=True)
    is_active    = models.BooleanField(default=True)
    start_time   = models.DateTimeField(null=True, blank=True)
    end_time     = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.session_name} ({'open' if self.is_active else 'closed'})"

    class Meta:
        ordering = ['-created_at']


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT   = 'PRESENT',   'Present'
        EXCUSED   = 'EXCUSED',   'Excused'
        UNEXCUSED = 'UNEXCUSED', 'Unexcused'

    session       = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    member        = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='attendance_records')
    checked_in_at = models.DateTimeField(auto_now_add=True)
    status        = models.CharField(max_length=10, choices=Status.choices, default=Status.PRESENT)

    def __str__(self):
        return f"{self.member.full_name} @ {self.session.session_name} ({self.status})"

    class Meta:
        unique_together = ('session', 'member')
        ordering = ['-checked_in_at']


class Meeting(models.Model):
    title              = models.CharField(max_length=200)
    date               = models.DateField()
    created_by         = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name='meetings_created')
    attendance_session = models.OneToOneField(AttendanceSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='meeting')
    scheduled_start    = models.DateTimeField(null=True, blank=True)
    scheduled_end      = models.DateTimeField(null=True, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.date})"

    class Meta:
        ordering = ['-date']


class Agenda(models.Model):
    meeting              = models.OneToOneField(Meeting, on_delete=models.CASCADE, related_name='agenda')
    presiding_officer    = models.CharField(max_length=120, blank=True)
    quorum_confirmed     = models.BooleanField(default=False)
    agenda_approved      = models.BooleanField(default=False)
    called_to_order_time = models.DateTimeField(null=True, blank=True)
    next_meeting_date    = models.DateField(null=True, blank=True)
    adjourned_time       = models.DateTimeField(null=True, blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Agenda – {self.meeting.title}"


class AgendaSection(models.Model):
    SECTION_CHOICES = [
        ('OPENING',       'Opening'),
        ('ANNOUNCEMENTS', 'Announcements'),
        ('REPORTS',       'Officer and Committee Reports'),
        ('UNFINISHED',    'Unfinished Business'),
        ('NEW',           'New Business'),
        ('OPEN_FLOOR',    'Open Floor'),
        ('ADJOURNMENT',   'Adjournment'),
    ]
    SECTION_ORDER = ['OPENING', 'ANNOUNCEMENTS', 'REPORTS', 'UNFINISHED', 'NEW', 'OPEN_FLOOR', 'ADJOURNMENT']

    agenda       = models.ForeignKey(Agenda, on_delete=models.CASCADE, related_name='sections')
    section_type = models.CharField(max_length=20, choices=SECTION_CHOICES)
    is_hidden    = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_section_type_display()} – {self.agenda.meeting.title}"

    class Meta:
        ordering = ['id']


class AgendaItem(models.Model):
    STATUS_CHOICES = [
        ('',            'None'),
        ('PASSED',      'Passed'),
        ('TABLED',      'Tabled'),
        ('POSTPONED',   'Postponed Indefinitely'),
        ('DILATED',     'Dilated'),
    ]

    section      = models.ForeignKey(AgendaSection, on_delete=models.CASCADE, related_name='items')
    text         = models.TextField()
    order        = models.IntegerField(default=0)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, default='')
    notes        = models.TextField(blank=True)
    carried_from = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='carried_to')
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text[:50]} ({self.section.get_section_type_display()})"

    class Meta:
        ordering = ['order', 'id']


class AgendaSubItem(models.Model):
    item  = models.ForeignKey(AgendaItem, on_delete=models.CASCADE, related_name='subitems')
    text  = models.TextField()
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"  – {self.text[:50]}"

    class Meta:
        ordering = ['order', 'id']


class Committee(models.Model):
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class CommitteeMember(models.Model):
    member    = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='committee_memberships')
    committee = models.ForeignKey(Committee, on_delete=models.CASCADE, related_name='members')
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.full_name} - {self.committee.name}"

    class Meta:
        unique_together = ('member', 'committee')


class Announcement(models.Model):
    title        = models.CharField(max_length=200)
    body         = models.TextField()
    is_published = models.BooleanField(default=False)
    created_by   = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, related_name='announcements')
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({'published' if self.is_published else 'draft'})"

    class Meta:
        ordering = ['-created_at']


class SiteSettings(models.Model):
    signup_enabled = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        verbose_name = 'Site settings'