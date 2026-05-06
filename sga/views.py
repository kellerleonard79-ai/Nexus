from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import (
    Member, SiteSettings, Announcement, Meeting,
    AttendanceSession, AttendanceRecord,
    Agenda, AgendaSection, AgendaItem, AgendaSubItem,
)
import uuid
import qrcode
import io
import base64
import json
from datetime import datetime, date


def test_view(request):
    return HttpResponse('<html><body><h1>It works</h1></body></html>', content_type='text/html')


def home_view(request):
    announcements = Announcement.objects.filter(is_published=True).order_by('-created_at')[:5]
    settings = SiteSettings.get()
    return render(request, 'sga/home.html', {
        'announcements': announcements,
        'signup_enabled': settings.signup_enabled,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        student_id = request.POST.get('student_id', '').strip()
        password   = request.POST.get('password', '')
        user = authenticate(request, username=student_id, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid student ID or password.')
    return render(request, 'sga/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


def signup_view(request):
    settings = SiteSettings.get()
    if not settings.signup_enabled:
        return redirect('home')
    if request.method == 'POST':
        full_name  = request.POST.get('full_name', '').strip()
        student_id = request.POST.get('student_id', '').strip()
        grade      = request.POST.get('grade', '').strip()
        shirt_size = request.POST.get('shirt_size', '').strip()
        email      = request.POST.get('email', '').strip()
        password   = request.POST.get('password', '')
        confirm_pw = request.POST.get('confirm_password', '')
        if not student_id.isdigit() or len(student_id) != 6:
            messages.error(request, 'Student ID must be exactly 6 digits.')
            return render(request, 'sga/signup.html')
        if password != confirm_pw:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'sga/signup.html')
        if User.objects.filter(username=student_id).exists():
            messages.error(request, 'An account with that Student ID already exists.')
            return render(request, 'sga/signup.html')
        User.objects.create_user(username=student_id, password=password, email=email)
        Member.objects.create(
            student_id=student_id,
            full_name=full_name,
            grade=grade,
            shirt_size=shirt_size,
            email=email,
            permission_tier='APPLICANT',
            member_status='PENDING',
        )
        messages.success(request, 'Account created! You can now log in.')
        return redirect('login')
    return render(request, 'sga/signup.html')


def about_view(request):
    exec_officers = Member.objects.filter(
        elected_position__in=['EXEC_PRES', 'EXEC_VP', 'EXEC_PARL', 'EXEC_SEC', 'EXEC_TRES']
    ).order_by('elected_position')
    class_groups = [
        ('Senior',    ['SR_PRES', 'SR_VP', 'SR_SEC']),
        ('Junior',    ['JR_PRES', 'JR_VP', 'JR_SEC']),
        ('Sophomore', ['SO_PRES', 'SO_VP', 'SO_SEC']),
        ('Freshman',  ['FR_PRES', 'FR_VP', 'FR_SEC']),
    ]
    class_officers_grouped = []
    for label, positions in class_groups:
        officers = Member.objects.filter(elected_position__in=positions).order_by('elected_position')
        class_officers_grouped.append({'label': label, 'officers': officers})
    return render(request, 'sga/about.html', {
        'exec_officers': exec_officers,
        'class_officers_grouped': class_officers_grouped,
    })


def is_officer(member):
    return member.permission_tier in ('OFFICER', 'SCI')


@login_required
def dashboard_view(request):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        messages.error(request, 'No member record found for your account.')
        return redirect('login')
    settings = SiteSettings.get()
    if request.method == 'POST' and is_officer(member):
        action = request.POST.get('action')
        if action == 'toggle_signup':
            settings.signup_enabled = not settings.signup_enabled
            settings.save()
        return redirect('dashboard')
    return render(request, 'sga/dashboard.html', {
        'member': member,
        'signup_enabled': settings.signup_enabled,
    })

@login_required
def edit_site_view(request):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(member):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    settings = SiteSettings.get()
    announcements = Announcement.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'toggle_signup':
            settings.signup_enabled = not settings.signup_enabled
            settings.save()
            messages.success(request, f'Join SGA button {"shown" if settings.signup_enabled else "hidden"}.')
        
        elif action == 'create_announcement':
            title = request.POST.get('title', '').strip()
            body = request.POST.get('body', '').strip()
            is_published = bool(request.POST.get('is_published'))
            if title and body:
                Announcement.objects.create(
                    title=title,
                    body=body,
                    is_published=is_published,
                    created_by=member
                )
                messages.success(request, 'Announcement created.')
            else:
                messages.error(request, 'Title and body are required.')
        
        elif action == 'edit_announcement':
            ann_id = request.POST.get('announcement_id')
            ann = Announcement.objects.filter(id=ann_id).first()
            if ann:
                ann.title = request.POST.get('title', ann.title).strip()
                ann.body = request.POST.get('body', ann.body).strip()
                ann.is_published = bool(request.POST.get('is_published'))
                ann.save()
                messages.success(request, 'Announcement updated.')
        
        elif action == 'delete_announcement':
            ann_id = request.POST.get('announcement_id')
            Announcement.objects.filter(id=ann_id).delete()
            messages.success(request, 'Announcement deleted.')
        
        return redirect('edit_site')
    
    return render(request, 'sga/edit_site.html', {
        'member': member,
        'settings': settings,
        'announcements': announcements,
    })

@login_required
def directory_view(request):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(member):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    # Handle dues toggle
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'toggle_dues':
            student_id = request.POST.get('student_id')
            target = Member.objects.filter(student_id=student_id).first()
            if target:
                target.dues_status = 'PAID' if target.dues_status == 'PENDING' else 'PENDING'
                target.save()
        return redirect(request.get_full_path())
    
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '')
    dues_filter = request.GET.get('dues', '')
    tier_filter = request.GET.get('tier', '')
    
    members = Member.objects.all()
    
    if query:
        members = members.filter(full_name__icontains=query)
    
    if dues_filter:
        members = members.filter(dues_status=dues_filter)
    
    if tier_filter:
        members = members.filter(permission_tier=tier_filter)
    
    # Sorting
    if sort_by == 'attendance':
        # Annotate with attendance counts and sort by worst attendance
        from django.db.models import Count, Q
        members = members.annotate(
            unexcused_count=Count('attendance_records', filter=Q(attendance_records__status='UNEXCUSED')),
            excused_count=Count('attendance_records', filter=Q(attendance_records__status='EXCUSED'))
        ).order_by('-unexcused_count', '-excused_count', 'full_name')
    else:
        members = members.order_by('full_name')
    
    return render(request, 'sga/directory.html', {
        'members': members,
        'query': query,
        'member': member,
        'sort_by': sort_by,
        'dues_filter': dues_filter,
        'tier_filter': tier_filter,
    })

@login_required
def profile_view(request):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    records = member.attendance_records.select_related('session').order_by('-checked_in_at')
    return render(request, 'sga/profile.html', {
        'member': member,
        'viewing_self': True,
        'records': records,
    })


@login_required
def member_profile_view(request, student_id):
    try:
        viewer = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(viewer):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    target = Member.objects.filter(student_id=student_id).first()
    if not target:
        messages.error(request, 'Member not found.')
        return redirect('directory')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_tier':
            new_tier = request.POST.get('permission_tier')
            if new_tier in ('APPLICANT', 'OFFICER', 'SCI'):
                target.permission_tier = new_tier
                target.save()
                messages.success(request, f'{target.full_name} updated to {new_tier}.')
        elif action == 'update_position':
            new_position = request.POST.get('elected_position', '')
            target.elected_position = new_position
            target.save()
            messages.success(request, f"{target.full_name}'s position updated.")
        elif action == 'dismiss_warning':
            target.attendance_warning_dismissed = True
            target.save()
            messages.success(request, 'Attendance warning dismissed.')
        elif action == 'delete_member':
            name = target.full_name
            User.objects.filter(username=target.student_id).delete()
            target.delete()
            messages.success(request, f'{name} has been removed.')
            return redirect('directory')
        return redirect('member_profile', student_id=student_id)
    records = target.attendance_records.select_related('session').order_by('-checked_in_at')
    return render(request, 'sga/profile.html', {
        'member': target,
        'viewer': viewer,
        'viewing_self': False,
        'records': records,
    })


@login_required
def delete_member_view(request, student_id):
    try:
        viewer = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(viewer):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    if request.method == 'POST':
        target = Member.objects.filter(student_id=student_id).first()
        if target:
            name = target.full_name
            User.objects.filter(username=target.student_id).delete()
            target.delete()
            messages.success(request, f'{name} has been removed.')
    return redirect('directory')


# ─── Meetings ──────────────────────────────────────────────────────────────────

@login_required
def meetings_view(request):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(member):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    today    = date.today()
    upcoming = Meeting.objects.filter(date__gte=today).order_by('date')
    query    = request.GET.get('q', '')
    past     = Meeting.objects.filter(date__lt=today).order_by('-date')
    if query:
        past = past.filter(title__icontains=query)

    return render(request, 'sga/meetings.html', {
        'member': member,
        'upcoming': upcoming,
        'past': past,
        'query': query,
        'today': today,
    })


@login_required
def create_meeting_view(request):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(member):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        date_str    = request.POST.get('date', '').strip()
        use_default = request.POST.get('use_default', '')

        if not date_str:
            messages.error(request, 'Please select a date.')
            return render(request, 'sga/create_meeting.html', {'member': member})

        try:
            meeting_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date.')
            return render(request, 'sga/create_meeting.html', {'member': member})

        formatted_date = meeting_date.strftime('%B %-d, %Y')

        if use_default or not title:
            final_title = f'SGA Meeting \u2013 {formatted_date}'
        else:
            final_title = f'{title} \u2013 {formatted_date}'

        meeting = Meeting.objects.create(
            title=final_title,
            date=meeting_date,
            created_by=member,
        )
        return redirect('meeting_detail', meeting_id=meeting.id)

    return render(request, 'sga/create_meeting.html', {'member': member})


@login_required
def meeting_detail_view(request, meeting_id):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(member):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    meeting = Meeting.objects.filter(id=meeting_id).first()
    if not meeting:
        messages.error(request, 'Meeting not found.')
        return redirect('meetings')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_qr':
            start_time_str = request.POST.get('start_time', '').strip()
            end_time_str   = request.POST.get('end_time', '').strip()
            scheduled      = request.POST.get('scheduled', '')

            token = uuid.uuid4().hex
            session = AttendanceSession(
                session_name=meeting.title,
                created_by=member,
                qr_token=token,
                is_active=not bool(scheduled),
            )
            if start_time_str:
                session.start_time = timezone.make_aware(datetime.fromisoformat(start_time_str))
            if end_time_str:
                session.end_time = timezone.make_aware(datetime.fromisoformat(end_time_str))
            session.save()

            meeting.attendance_session = session
            if start_time_str:
                meeting.scheduled_start = session.start_time
            if end_time_str:
                meeting.scheduled_end = session.end_time
            meeting.save()
            return redirect('session_qr', token=token)

        elif action == 'delete_meeting':
            meeting.delete()
            messages.success(request, 'Meeting deleted.')
            return redirect('meetings')

        elif action == 'edit_title':
            new_title = request.POST.get('new_title', '').strip()
            if new_title:
                meeting.title = new_title
                meeting.save()

        return redirect('meeting_detail', meeting_id=meeting_id)

    # Auto open/close QR session
    if meeting.attendance_session:
        session = meeting.attendance_session
        now = timezone.now()
        if session.start_time and session.end_time:
            should_be_active = session.start_time <= now <= session.end_time
            if session.is_active != should_be_active:
                session.is_active = should_be_active
                session.save()

    qr_b64 = None
    checkin_url = None
    if meeting.attendance_session:
        checkin_url = request.build_absolute_uri(f'/checkin/{meeting.attendance_session.qr_token}/')
        qr = qrcode.QRCode(version=1, box_size=6, border=3)
        qr.add_data(checkin_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    has_agenda = hasattr(meeting, 'agenda')

    return render(request, 'sga/meeting_detail.html', {
        'member': member,
        'meeting': meeting,
        'qr_b64': qr_b64,
        'checkin_url': checkin_url,
        'has_agenda': has_agenda,
    })


# ─── Agenda ────────────────────────────────────────────────────────────────────

def _get_or_create_agenda(meeting):
    """Get or create agenda with all 7 sections."""
    agenda, created = Agenda.objects.get_or_create(meeting=meeting)
    if created:
        section_types = AgendaSection.SECTION_ORDER
        for st in section_types:
            AgendaSection.objects.create(agenda=agenda, section_type=st)
    return agenda


@login_required
def agenda_view(request, meeting_id):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(member):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    meeting = Meeting.objects.filter(id=meeting_id).first()
    if not meeting:
        messages.error(request, 'Meeting not found.')
        return redirect('meetings')

    agenda = _get_or_create_agenda(meeting)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_item':
            section_id = request.POST.get('section_id')
            text = request.POST.get('text', '').strip()
            if text:
                section = AgendaSection.objects.filter(id=section_id, agenda=agenda).first()
                if section:
                    max_order = section.items.count()
                    AgendaItem.objects.create(section=section, text=text, order=max_order)

        elif action == 'add_subitem':
            item_id = request.POST.get('item_id')
            text = request.POST.get('text', '').strip()
            if text:
                item = AgendaItem.objects.filter(id=item_id, section__agenda=agenda).first()
                if item:
                    max_order = item.subitems.count()
                    AgendaSubItem.objects.create(item=item, text=text, order=max_order)

        elif action == 'update_item':
            item_id = request.POST.get('item_id')
            item = AgendaItem.objects.filter(id=item_id, section__agenda=agenda).first()
            if item:
                item.text   = request.POST.get('text', item.text).strip() or item.text
                item.status = request.POST.get('status', item.status)
                item.notes  = request.POST.get('notes', item.notes)
                item.save()

        elif action == 'delete_item':
            item_id = request.POST.get('item_id')
            AgendaItem.objects.filter(id=item_id, section__agenda=agenda).delete()

        elif action == 'delete_subitem':
            subitem_id = request.POST.get('subitem_id')
            AgendaSubItem.objects.filter(id=subitem_id, item__section__agenda=agenda).delete()

        elif action == 'toggle_section':
            section_id = request.POST.get('section_id')
            section = AgendaSection.objects.filter(id=section_id, agenda=agenda).first()
            if section and section.items.count() == 0:
                section.is_hidden = not section.is_hidden
                section.save()

        elif action == 'update_opening':
            agenda.presiding_officer = request.POST.get('presiding_officer', agenda.presiding_officer)
            agenda.quorum_confirmed  = bool(request.POST.get('quorum_confirmed'))
            agenda.agenda_approved   = bool(request.POST.get('agenda_approved'))
            cto = request.POST.get('called_to_order_time', '').strip()
            if cto:
                try:
                    agenda.called_to_order_time = timezone.make_aware(datetime.fromisoformat(cto))
                except ValueError:
                    pass
            agenda.save()

        elif action == 'update_adjournment':
            nmd = request.POST.get('next_meeting_date', '').strip()
            if nmd:
                try:
                    agenda.next_meeting_date = datetime.strptime(nmd, '%Y-%m-%d').date()
                except ValueError:
                    pass
            adj = request.POST.get('adjourned_time', '').strip()
            if adj:
                try:
                    agenda.adjourned_time = timezone.make_aware(datetime.fromisoformat(adj))
                except ValueError:
                    pass
            agenda.save()

        elif action == 'sync_qr':
            session = meeting.attendance_session
            if session:
                if session.created_at and not agenda.called_to_order_time:
                    agenda.called_to_order_time = session.created_at
                if not session.is_active and session.end_time and not agenda.adjourned_time:
                    agenda.adjourned_time = session.end_time
                agenda.save()
                messages.success(request, 'Synced times from QR session.')

        elif action == 'carry_tabled':
            tabled_items = AgendaItem.objects.filter(
                section__agenda=agenda,
                status='TABLED'
            )
            next_meeting = Meeting.objects.filter(date__gt=meeting.date).order_by('date').first()
            if not next_meeting:
                messages.error(request, 'No future meeting found to carry items to.')
            elif tabled_items.count() == 0:
                messages.error(request, 'No tabled items to carry forward.')
            else:
                next_agenda = _get_or_create_agenda(next_meeting)
                unfinished  = next_agenda.sections.filter(section_type='UNFINISHED').first()
                if unfinished:
                    carried = 0
                    for item in tabled_items:
                        already_carried = AgendaItem.objects.filter(
                            carried_from=item,
                            section__agenda=next_agenda
                        ).exists()
                        if not already_carried:
                            max_order = unfinished.items.count()
                            AgendaItem.objects.create(
                                section=unfinished,
                                text=f'[Tabled from {meeting.date}] {item.text}',
                                order=max_order,
                                carried_from=item,
                            )
                            carried += 1
                    messages.success(request, f'{carried} tabled item(s) carried to {next_meeting.title}.')

        return redirect('agenda', meeting_id=meeting_id)

    sections = agenda.sections.prefetch_related('items__subitems').all()
    qr_b64 = None
    checkin_url = None
    if meeting.attendance_session:
        checkin_url = request.build_absolute_uri(f'/checkin/{meeting.attendance_session.qr_token}/')
        qr = qrcode.QRCode(version=1, box_size=5, border=3)
        qr.add_data(checkin_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'sga/agenda_editor.html', {
        'member': member,
        'meeting': meeting,
        'agenda': agenda,
        'sections': sections,
        'qr_b64': qr_b64,
        'checkin_url': checkin_url,
    })


@login_required
@require_POST
def agenda_reorder_view(request, meeting_id):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return JsonResponse({'error': 'unauthorized'}, status=403)
    if not is_officer(member):
        return JsonResponse({'error': 'forbidden'}, status=403)

    meeting = Meeting.objects.filter(id=meeting_id).first()
    if not meeting or not hasattr(meeting, 'agenda'):
        return JsonResponse({'error': 'not found'}, status=404)

    try:
        data = json.loads(request.body)
        item_ids = data.get('item_ids', [])
        for index, item_id in enumerate(item_ids):
            AgendaItem.objects.filter(
                id=item_id, section__agenda=meeting.agenda
            ).update(order=index)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def public_agenda_view(request, meeting_id):
    meeting = Meeting.objects.filter(id=meeting_id).first()
    if not meeting:
        return redirect('home')

    checked_in = request.GET.get('checkedin', '')
    agenda = None
    sections = []

    if hasattr(meeting, 'agenda'):
        agenda = meeting.agenda
        sections = agenda.sections.prefetch_related('items__subitems').filter(is_hidden=False)

    qr_b64 = None
    if meeting.attendance_session and meeting.attendance_session.is_active:
        checkin_url = request.build_absolute_uri(f'/checkin/{meeting.attendance_session.qr_token}/')
        qr = qrcode.QRCode(version=1, box_size=4, border=2)
        qr.add_data(checkin_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'sga/public_agenda.html', {
        'meeting': meeting,
        'agenda': agenda,
        'sections': sections,
        'qr_b64': qr_b64,
        'checked_in': checked_in,
    })


# ─── Attendance ─────────────────────────────────────────────────────────────────

@login_required
def attendance_view(request):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(member):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    if request.method == 'POST':
        session_name = request.POST.get('session_name', '').strip()
        start_time   = request.POST.get('start_time', '').strip()
        end_time     = request.POST.get('end_time', '').strip()
        if session_name:
            token = uuid.uuid4().hex
            session = AttendanceSession(
                session_name=session_name,
                created_by=member,
                qr_token=token,
                is_active=True,
            )
            if start_time:
                session.start_time = timezone.make_aware(datetime.fromisoformat(start_time))
            if end_time:
                session.end_time = timezone.make_aware(datetime.fromisoformat(end_time))
            session.save()
            return redirect('session_qr', token=token)
        else:
            messages.error(request, 'Please enter a session name.')

    date_filter = request.GET.get('date', '')
    sessions = AttendanceSession.objects.all().order_by('-created_at')
    if date_filter:
        sessions = sessions.filter(created_at__date=date_filter)
    sessions = sessions[:50]

    return render(request, 'sga/attendance.html', {
        'member': member,
        'sessions': sessions,
        'date_filter': date_filter,
    })


@login_required
def session_qr_view(request, token):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if not is_officer(member):
        return redirect('dashboard')

    session = AttendanceSession.objects.filter(qr_token=token).first()
    if not session:
        messages.error(request, 'Session not found.')
        return redirect('attendance')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'close':
            session.is_active = False
            session.save()
        elif action == 'reopen':
            session.is_active = True
            session.save()
        elif action == 'update_status':
            target_sid = request.POST.get('target_student_id', '').strip()
            new_status = request.POST.get('status', '')
            if new_status in ('PRESENT', 'EXCUSED', 'UNEXCUSED'):
                target_member = Member.objects.filter(student_id=target_sid).first()
                if target_member:
                    record, created = AttendanceRecord.objects.get_or_create(
                        session=session, member=target_member,
                        defaults={'status': new_status}
                    )
                    if not created:
                        record.status = new_status
                        record.save()
            elif new_status == 'REMOVE':
                target_member = Member.objects.filter(student_id=target_sid).first()
                if target_member:
                    AttendanceRecord.objects.filter(session=session, member=target_member).delete()
        return redirect('session_qr', token=token)

    officers_with_positions = Member.objects.exclude(elected_position='')
    total_officers = officers_with_positions.count()
    present_count  = AttendanceRecord.objects.filter(session=session, status='PRESENT').count()
    quorum_needed  = (total_officers // 2) + 1
    quorum_met     = total_officers > 0 and present_count >= quorum_needed

    member_search = request.GET.get('ms', '')
    all_members = Member.objects.all().order_by('full_name')
    if member_search:
        all_members = all_members.filter(full_name__icontains=member_search)

    existing_records = {r.member_id: r for r in AttendanceRecord.objects.filter(session=session)}
    member_attendance = []
    for m in all_members:
        record = existing_records.get(m.id)
        member_attendance.append({'member': m, 'status': record.status if record else None})

    checkin_url = request.build_absolute_uri(f'/checkin/{token}/')
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(checkin_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_b64 = base64.b64encode(buffer.getvalue()).decode()

    records = AttendanceRecord.objects.filter(session=session).order_by('-checked_in_at')
    meeting = getattr(session, 'meeting', None)

    return render(request, 'sga/session_qr.html', {
        'member': member,
        'session': session,
        'meeting': meeting,
        'qr_b64': qr_b64,
        'checkin_url': checkin_url,
        'records': records,
        'present_count': present_count,
        'total_members': Member.objects.count(),
        'total_officers': total_officers,
        'quorum_needed': quorum_needed,
        'quorum_met': quorum_met,
        'member_attendance': member_attendance,
        'member_search': member_search,
    })


def checkin_view(request, token):
    session = AttendanceSession.objects.filter(qr_token=token, is_active=True).first()

    if not session:
        return render(request, 'sga/checkin.html', {
            'error': 'This check-in session is not active.',
            'session': None,
        })

    now = timezone.now()
    if session.start_time and now < session.start_time:
        return render(request, 'sga/checkin.html', {
            'session': session,
            'error': f'Check-in does not open until {session.start_time.strftime("%-I:%M %p")}.',
        })
    if session.end_time and now > session.end_time:
        return render(request, 'sga/checkin.html', {
            'session': session,
            'error': f'Check-in closed at {session.end_time.strftime("%-I:%M %p")}.',
        })

    if request.method == 'POST':
        student_id = request.POST.get('student_id', '').strip()
        if not student_id.isdigit() or len(student_id) != 6:
            return render(request, 'sga/checkin.html', {
                'session': session,
                'error': 'Please enter a valid 6-digit student ID.',
            })
        member = Member.objects.filter(student_id=student_id).first()
        if not member:
            return render(request, 'sga/checkin.html', {
                'session': session,
                'error': 'Student ID not found. Make sure you have an SGA account.',
            })
        already = AttendanceRecord.objects.filter(session=session, member=member).exists()
        if already:
            return render(request, 'sga/checkin.html', {
                'session': session,
                'error': 'You have already checked in to this session.',
            })
        AttendanceRecord.objects.create(session=session, member=member, status='PRESENT')

        meeting = getattr(session, 'meeting', None)
        if meeting:
            return redirect(f'/agenda/{meeting.id}/public/?checkedin=1')

        return render(request, 'sga/checkin.html', {
            'session': session,
            'success': f'Checked in! Welcome, {member.full_name}.',
        })

    return render(request, 'sga/checkin.html', {'session': session})

# ─── Bookkeeping ───────────────────────────────────────────────────────────────

@login_required
def bookkeeping_view(request):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if member.permission_tier != 'SCI':
        messages.error(request, 'Access denied. SCI members only.')
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create_account':
            name = request.POST.get('name', '').strip()
            starting_balance = request.POST.get('starting_balance', '0')
            if name:
                try:
                    balance = float(starting_balance.replace(',', ''))
                    Account.objects.create(name=name, starting_balance=balance)
                    messages.success(request, f'Account "{name}" created.')
                except ValueError:
                    messages.error(request, 'Invalid starting balance.')
            else:
                messages.error(request, 'Account name is required.')
        
        elif action == 'edit_balance':
            account_id = request.POST.get('account_id')
            new_balance = request.POST.get('new_balance', '0')
            account = Account.objects.filter(id=account_id).first()
            if account:
                try:
                    balance = float(new_balance.replace(',', ''))
                    account.starting_balance = balance
                    account.save()
                    messages.success(request, f'Starting balance updated for "{account.name}".')
                except ValueError:
                    messages.error(request, 'Invalid balance value.')
        
        elif action == 'delete_account':
            account_id = request.POST.get('account_id')
            account = Account.objects.filter(id=account_id).first()
            if account:
                name = account.name
                account.delete()
                messages.success(request, f'Account "{name}" deleted.')
        
        return redirect('bookkeeping')

    accounts = Account.objects.all()
    return render(request, 'sga/bookkeeping.html', {
        'member': member,
        'accounts': accounts,
    })


@login_required
def account_detail_view(request, account_id):
    try:
        member = Member.objects.get(student_id=request.user.username)
    except Member.DoesNotExist:
        return redirect('login')
    if member.permission_tier != 'SCI':
        messages.error(request, 'Access denied. SCI members only.')
        return redirect('dashboard')

    account = Account.objects.filter(id=account_id).first()
    if not account:
        messages.error(request, 'Account not found.')
        return redirect('bookkeeping')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_transaction':
            date_str = request.POST.get('date', '')
            credit_str = request.POST.get('credit', '').strip()
            debit_str = request.POST.get('debit', '').strip()
            notes = request.POST.get('notes', '').strip()
            
            try:
                trans_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
                credit = float(credit_str.replace(',', '')) if credit_str else None
                debit = float(debit_str.replace(',', '')) if debit_str else None
                
                if credit and debit:
                    messages.error(request, 'Cannot have both credit and debit in one transaction.')
                elif not credit and not debit:
                    messages.error(request, 'Must specify either credit or debit.')
                else:
                    Transaction.objects.create(
                        account=account,
                        date=trans_date,
                        credit=credit,
                        debit=debit,
                        notes=notes,
                        created_by=member
                    )
                    messages.success(request, 'Transaction added.')
            except ValueError:
                messages.error(request, 'Invalid date or amount.')
        
        elif action == 'edit_transaction':
            trans_id = request.POST.get('transaction_id')
            transaction = Transaction.objects.filter(id=trans_id, account=account).first()
            if transaction:
                date_str = request.POST.get('date', '')
                credit_str = request.POST.get('credit', '').strip()
                debit_str = request.POST.get('debit', '').strip()
                notes = request.POST.get('notes', '').strip()
                
                try:
                    transaction.date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else transaction.date
                    transaction.credit = float(credit_str.replace(',', '')) if credit_str else None
                    transaction.debit = float(debit_str.replace(',', '')) if debit_str else None
                    transaction.notes = notes
                    
                    if transaction.credit and transaction.debit:
                        messages.error(request, 'Cannot have both credit and debit in one transaction.')
                    elif not transaction.credit and not transaction.debit:
                        messages.error(request, 'Must specify either credit or debit.')
                    else:
                        transaction.save()
                        messages.success(request, 'Transaction updated.')
                except ValueError:
                    messages.error(request, 'Invalid date or amount.')
        
        elif action == 'delete_transaction':
            trans_id = request.POST.get('transaction_id')
            Transaction.objects.filter(id=trans_id, account=account).delete()
            messages.success(request, 'Transaction deleted.')
        
        return redirect('account_detail', account_id=account_id)

    transactions = account.transactions.all()

    # Calculate running balance for each transaction
    running_balance = account.starting_balance
    trans_with_balance = []
    for trans in reversed(list(transactions)):
        if trans.credit:
            running_balance += trans.credit
        if trans.debit:
            running_balance -= trans.debit
        trans.balance_after = running_balance
        trans_with_balance.append(trans)
    
    trans_with_balance.reverse()
    return render(request, 'sga/account_detail.html', {
        'member': member,
        'account': account,
        'transactions': trans_with_balance,
        'today': date.today(),
    })