from wheel2deb import parse_args


def test():
    args = ['--map', 'attrs=attr', '--python-version', '1']
    parser = parse_args(args)
    assert parser.map['attrs'] == 'attr'
    assert parser.python_version == '1'
