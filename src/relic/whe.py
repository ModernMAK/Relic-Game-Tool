from relic import chunky


def raw_dump():
    chunky.dump_all_chunky(r"D:\Dumps\DOW I\sga", r"D:\Dumps\DOW I\whe-chunky", [".whe"])

if __name__ == "__main__":
    raw_dump()