def split_bits(value: int, *bit_widths: int) -> tuple[int, ...]:
    """按位宽从高位到低位拆分整数，返回各字段值的元组。

    Args:
        value: 待拆分的整数
        *bit_widths: 各字段的位宽，从高位到低位排列

    Returns:
        各字段值的元组，顺序与 bit_widths 一致

    Examples:
        >>> split_bits(458754, 16, 16)
        (7, 2)  # 即 (0x0007, 0x0002)
        >>> split_bits(0b10110001, 4, 4)
        (11, 1)  # 即 (0xB, 0x1)
    """
    parts: list[int] = []
    for width in reversed(bit_widths):
        mask = (1 << width) - 1
        parts.append(value & mask)
        value >>= width
    return tuple(reversed(parts))
