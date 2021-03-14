from _wheel2deb.apt import Package


def test_package_name_parsing():
    foo = Package.factory("foo", "1:12.04-r1~1")
    assert foo.epoch == "1" and foo.version == "12.04" and foo.revision == "r1~1"

    bar = Package.factory("bar", "3.0")
    assert bar.version == "3.0" and not bar.revision

    bar = Package.factory("bar", "3-1-1")
    assert bar.version == "3-1" and bar.revision == "1"
