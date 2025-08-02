def match_product(user_input, product_list):
    user_input_lower = user_input.lower()
    for product in product_list:
        product_name = product.get('name', '').lower()
        if product_name and product_name in user_input_lower:
            return product
    return None
