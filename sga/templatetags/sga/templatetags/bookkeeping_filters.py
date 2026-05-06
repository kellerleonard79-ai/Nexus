from django import template

register = template.Library()

@register.filter
def sum_credits(transactions):
    """Calculate total credits from a queryset of transactions"""
    return sum(t.credit for t in transactions if t.credit) or 0

@register.filter
def sum_debits(transactions):
    """Calculate total debits from a queryset of transactions"""
    return sum(t.debit for t in transactions if t.debit) or 0