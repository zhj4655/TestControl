#
# OtterTune - PostgresConf.py
#
# Add by zhj 2018.10.4
#


import sys
import json
from collections import OrderedDict
import random

def main():
    if (len(sys.argv) != 3):
        raise Exception("Usage: python confparser.py [Next Config] [Current Config]")

    with open(sys.argv[1], "r") as f:
        conf = json.load(f,
                         encoding="UTF-8",
                         object_pairs_hook=OrderedDict)
    conf = conf['recommendation']
    with open(sys.argv[2], "r+") as mysqlconf:
        lines = mysqlconf.readlines()
        settings_idx = lines.index("# Add settings for extensions here\n")
        mysqlconf.seek(0)
        mysqlconf.truncate(0)

        lines = lines[0:(settings_idx + 1)]
        for line in lines:
            mysqlconf.write(line)

        for (knob_name, knob_value) in list(conf.items()):
            res = float(knob_value) - random.randint(0,int(int(knob_value)*99))/100.0
            if res - int(res) >= 0.5:
                res = int(res)+1
            else:
                res = int(res) 
            conf[knob_name] = res
            # if conf[knob_name] == 0:
            #     conf[knob_name] = conf[knob_name] + 1

        # print(conf)
        for (knob_name, knob_value) in list(conf.items()):
            mysqlconf.write(str(knob_name) + " = " + str(knob_value) + "\n")
            # print(knob_value)


if __name__ == "__main__":
    main()
