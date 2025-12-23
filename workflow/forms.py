from django import forms
from core.models import Etapa, Checklist


class EtapaForm(forms.ModelForm):
    class Meta:
        model = Etapa
        fields = ['nome', 'sequencia', 'ativa', 'se_gera_pontos', 'se_possui_checklists', 
                  'se_possui_calculo_por_quantidade', 'pontos_fixos_etapa']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da etapa'
            }),
            'sequencia': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sequência (ex: 1, 2, 3...',
                'min': '0'
            }),
            'ativa': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'se_gera_pontos': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'se_possui_checklists': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'se_possui_calculo_por_quantidade': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'pontos_fixos_etapa': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Pontos fixos ao concluir a etapa',
                'step': '0.01',
                'min': '0'
            }),
        }


class ChecklistForm(forms.ModelForm):
    class Meta:
        model = Checklist
        fields = ['nome', 'descricao', 'pontos_do_check', 'obrigatorio', 'ativo', 'ordem']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome do checklist'
            }),
            'descricao': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Descrição (opcional)',
                'rows': 3
            }),
            'pontos_do_check': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Pontos',
                'step': '0.01'
            }),
            'obrigatorio': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'ordem': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ordem de exibição',
                'min': '0'
            }),
        }
