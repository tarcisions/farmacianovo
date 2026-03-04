"""
Helper para sincronização de dados da API com as fórmulas
"""
from datetime import datetime
from django.utils import timezone


def sincronizar_datetime_api(formula, dtalt_str=None, hralt_str=None):
    """
    Sincroniza a data e hora da API com o campo datetime_atualizacao_api
    
    Args:
        formula: instância de FormulaItem
        dtalt_str: Data no formato "YYYY-MM-DD" (ex: "2026-03-02")
        hralt_str: Hora no formato "HH:MM:SS" (ex: "17:50:56")
    
    Returns:
        Booleano indicando se houve atualização
    """
    if not dtalt_str or not hralt_str:
        return False
    
    try:
        # Combinar data + hora
        datetime_str = f"{dtalt_str} {hralt_str}"
        dt_api = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        
        # Converter para timezone aware (se usar timezone no Django)
        dt_api_aware = timezone.make_aware(dt_api)
        
        # Atualizar se for diferente
        if formula.datetime_atualizacao_api != dt_api_aware:
            formula.datetime_atualizacao_api = dt_api_aware
            formula.save(update_fields=['datetime_atualizacao_api'])
            return True
        
        return False
    
    except (ValueError, TypeError) as e:
        print(f"Erro ao processar data/hora da API: {e}")
        return False
