from decimal import Decimal, ROUND_HALF_UP

def calculate_complexity_charge(model: str, word_count: int, aspect_ratio: str, is_magic_expanded: bool = False) -> Decimal:
    base_costs = {
        'flux': Decimal('1.0'),
        'sdxl': Decimal('3.0'),
        'pro': Decimal('8.0'),
        'ultra': Decimal('15.0')
    }
    model_base = base_costs.get(model.lower(), Decimal('1.0'))
    
    word_extra = Decimal('0.0')
    if word_count > 80:
        word_extra = Decimal('2.0')
    elif word_count > 30:
        word_extra = Decimal('1.0')
        
    res_extra = Decimal('0.5') if aspect_ratio in ['16:9', '9:16'] else Decimal('0.0')
    magic_extra = Decimal('0.5') if is_magic_expanded else Decimal('0.0')
    
    raw_score = model_base + word_extra + res_extra + magic_extra
    rounded = raw_score.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
    # Range Clamping
    if model.lower() == 'flux':
        return min(max(rounded, Decimal('1')), Decimal('3'))
    elif model.lower() == 'sdxl':
        return min(max(rounded, Decimal('3')), Decimal('6'))
    elif model.lower() == 'pro':
        return min(max(rounded, Decimal('8')), Decimal('15'))
    else:
        return min(max(rounded, Decimal('15')), Decimal('22'))
