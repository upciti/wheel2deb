import attr
import re


@attr.s(frozen=True)
class Version:
    major = attr.ib(type=int, converter=int)
    minor = attr.ib(type=int, converter=int, default=0)
    micro = attr.ib(type=int, converter=int, default=0)

    @classmethod
    def from_str(cls, version_str):
        m = re.match(r"(\d)(?:\.(\d))?(?:\.(\d))?", version_str)
        v = list(map(lambda i: int(i) if i else 0, m.groups()))
        return cls(v[0], v[1], v[2])

    def inc(self):
        return Version(self.major, self.minor + 1, 0)

    def __str__(self):
        return (
            str(self.major)
            + "."
            + str(self.minor)
            + (("." + str(self.micro)) if self.micro else "")
        )


@attr.s(frozen=True)
class VersionRange:
    min = attr.ib(type=Version, default=None)
    max = attr.ib(type=Version, default=None)

    @max.validator
    def check(self, attribute, value):
        """ Enforce max > min. Interval must be open """
        if value and value <= self.min:
            raise ValueError("min must be strictly smaller than max")

    def __contains__(self, item):
        if self.min and self.max:
            return self.min <= item < self.max
        elif self.min:
            return self.min <= item
        elif self.max:
            return item < self.max
        else:
            return True
