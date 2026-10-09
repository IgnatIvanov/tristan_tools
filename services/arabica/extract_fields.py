def get_buyer_name(url_params: str|None):
    if url_params is None:
        return 'URL params not provided'
    if 'buyer_name' not in url_params:
        return 'buyer_name not in URL params'
    params_list = [el for el in url_params.split('&') if 'buyer_name' in el]
    buyer_name = params_list[0].replace('buyer_name=', '')
    return buyer_name

def get_tier(url_params: str|None):
    if url_params is None:
        return 'URL params not provided'
    if 'geo' not in url_params:
        return 'geo not in URL params'
    params_list = [el for el in url_params.split('&') if 'geo' in el]
    buyer_name = params_list[0].replace('geo=', '')
    return buyer_name

def get_art_name(url_params: str|None):
    if url_params is None:
        return 'URL params not provided'
    if 'creo_name' not in url_params:
        return 'creo_name not in URL params'
    params_list = [el for el in url_params.split('&') if 'creo_name' in el]
    buyer_name = params_list[0].replace('creo_name=', '')
    return buyer_name



# DEPRICATED

# def get_art_name(ad_name: str|None) -> str|None:
#     """Определение названия креатива 
#         по объявлениям фб Рината
#     """     
#     # 
#     if ad_name == '' or ad_name is None or type(ad_name) == float:
#         return None
#     # 
#     if '_' not in ad_name:
#         return ad_name
#     # 
#     suffix = ad_name.split('_')[-1]
#     for el in ['+--', '--+']:
#         suffix = suffix.replace(el, '')
#     suffix = suffix.strip()
#     return suffix

# def get_tier(name: str|None):
#     """Определение тира страны (гео) из названия объявления

#     Args:
#         fb_cam_name (str | None): _description_

#     Returns:
#         _type_: _description_
#     """    
#     if name is None: return '-'
#     parts = name.split('_')
#     if len(parts) == 1: return parts[0]
#     return parts[1]