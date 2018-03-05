from __future__ import with_statement


class SortableDict(dict):
    """Dictionary subclass that can return sorted items."""

    def sorteditems(self):
        return iter(sorted(self.iteritems()))


class DummyTime(object):
    """
    Dummy class to be used as a replacement for a float time object returned by time.time() on round-based votings.
    """

    def __iadd__(self, *args):  # Operator overload will return the object itself without any changes
        return self  # on assignment addition operations.


def fix_line(line):
    """Fix for the Client log line missing the \n (newline) character."""
    assert isinstance(line, str)
    while line[8:].startswith("Client "):
        line = line.split(":", 3)
        if len(line) < 4:  # If this bug is ever fixed within the MBII code,
            return ""  # make sure this fix is not processed.
        line[0] = int(line[0])  # Timestamp.
        for i in xrange(-1, -7, -1):
            substring = int(line[-2][i:])
            if (substring - line[0]) >= 0 or line[-2][(i - 1)] == " ":
                line = "%3i:%s" % (substring, line[-1])
                break
    return line


def remove_color(item):
    """Remove Quake3 color codes from a str object."""
    assert isinstance(item, str)
    for i in xrange(10):
        item = str.replace(item, "^%i" % (i), "")
    return item


def calculate_time(time1, time2):
    """Calculate time difference in hours:minutes:seconds format."""
    minutes, seconds = divmod(int((time2 - time1)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        time_type = "hour"
    elif minutes:
        time_type = "minute"
    else:
        time_type = "second"
    return ("%02i:%02i:%02i %s%s" % (hours, minutes, seconds, time_type,
                                     ("" if (hours + minutes + seconds) == 1 else "s")))


def tail(f, lines=20):
    total_lines_wanted = lines
    BLOCK_SIZE = 1024
    f.seek(0, 2)
    block_end_byte = f.tell()
    lines_to_go = total_lines_wanted
    block_number = -1
    blocks = []  # blocks of size BLOCK_SIZE, in reverse order starting
    # from the end of the file
    while lines_to_go > 0 and block_end_byte > 0:
        if (block_end_byte - BLOCK_SIZE > 0):
            # read the last block we haven't yet read
            f.seek(block_number * BLOCK_SIZE, 2)
            blocks.append(f.read(BLOCK_SIZE))
        else:
            # file too small, start from begining
            f.seek(0, 0)
            # only read what was not read
            blocks.append(f.read(block_end_byte))
        lines_found = blocks[-1].count('\n')
        lines_to_go -= lines_found
        block_end_byte -= BLOCK_SIZE
        block_number -= 1
    all_read_text = ''.join(reversed(blocks))
    return '\n'.join(all_read_text.splitlines()[-total_lines_wanted:])
