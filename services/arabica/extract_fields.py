def get_art_name(ad_name: str|None) -> str|None:
    """Определение названия креатива 
        по объявлениям фб Рината
    """     
    # 
    if ad_name == '' or ad_name is None or type(ad_name) == float:
        return None
    # 
    if '_' not in ad_name:
        return ad_name
    # 
    suffix = ad_name.split('_')[-1]
    for el in ['+--', '--+']:
        suffix = suffix.replace(el, '')
    suffix = suffix.strip()
    return suffix

def get_tier(name: str|None):
    """Определение тира страны (гео) из названия объявления

    Args:
        fb_cam_name (str | None): _description_

    Returns:
        _type_: _description_
    """    
    if name is None: return '-'
    parts = name.split('_')
    if len(parts) == 1: return parts[0]
    return parts[1]