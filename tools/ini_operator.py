# -*- coding: UTF-8 -*-
import os
import sys
if sys.version_info[0] == 2:
    import ConfigParser
else:
    import configparser as ConfigParser


# 去除python ConfigParser 库option字段被改小写的问题 #
class _MyConfigParser(ConfigParser.ConfigParser):
    def __init__(self, defaults=None):
        ConfigParser.ConfigParser.__init__(self, defaults=defaults)

    def optionxform(self, optionstr):
        return optionstr


class IniParser(object):

    def __init__(self, conf_path):
        self.conf_path = conf_path
        self.conf = _MyConfigParser()

    def get_all_sections(self):
        try:
            self.conf.read(self.conf_path)
            return self.conf.sections(), None
        except Exception as e:
            return None, str(e)

    def get_section_options(self, section):
        try:
            self.conf.read(self.conf_path)
            return self.conf.options(section), None
        except Exception as e:
            return None, str(e)

    def get_section_items(self, section):
        try:
            self.conf.read(self.conf_path)
            return self.conf.items(section), None
        except Exception as e:
            return None, str(e)

    def get_value(self, section, option):
        try:
            self.conf.read(self.conf_path)
            return self.conf.get(section, option), None
        except Exception as e:
            return None, str(e)

    def add_section(self, section):
        try:
            sections, _ = self.get_all_sections()
            if section not in sections:
                self.conf.add_section(section)
                self.conf.write(open(self.conf_path, "w"))
                return True, None
        except Exception as e:
            return False, str(e)

    def del_section(self, section):
        try:
            sections, _ = self.get_all_sections()
            if section in sections:
                self.conf.remove_section(section)
                self.conf.write(open(self.conf_path, "w"))
            return True, None
        except Exception as e:
            return False, str(e)

    def set_value(self, section, option, value):
        try:
            sections, err = self.get_all_sections()
            if not sections:
                raise Exception(err)
            if section not in sections:
                raise Exception('section: {0} is not exist'.format(section))
            self.conf.set(section, option, value)
            self.conf.write(open(self.conf_path, "w"))
            return True, None
        except Exception as e:
            return False, str(e)


def usage(oper=None):
    _use = {'get_sections': 'python %s get_sections <INIPATH>' % sys.argv[0],
            'add_section': 'python %s add_section <INIPATH> <SECTION>' % sys.argv[0],
            'del_section': 'python %s del_section <INIPATH> <SECTION>' % sys.argv[0],
            'get_options': 'python %s get_options <INIPATH> <SECTION>' % sys.argv[0],
            'get_value': 'python %s get_value <INIPATH> <SECTION> <OPTION>' % sys.argv[0],
            'set_value': 'python %s set_value <INIPATH> <SECTION> <OPTION> <VALUE>' % sys.argv[0]
            }
    if oper:
        return _use[oper]
    return '\n'.join(list(_use.values()))


def sys_err(msg):
    if msg:
        sys.stderr.write(str(msg)+'\n')
    sys.exit(1)


def main():
    argv_size = len(sys.argv)
    if argv_size < 3:
        sys_err(usage())
    operate, ini_file = sys.argv[1:3]
    if not os.path.isfile(ini_file):
        sys_err('%s not exist' % ini_file)

    parse = IniParser(ini_file)
    if operate == 'get_sections':
        print(' '.join(parse.get_all_sections()[0]))
    elif operate == 'add_section':
        if argv_size != 4:
            sys_err(usage(operate))
        parse.add_section(sys.argv[3])
    elif operate == 'del_section':
        if argv_size != 4:
            sys_err(usage(operate))
        parse.del_section(sys.argv[3])
    elif operate == 'get_options':
        if argv_size != 4:
            sys_err(usage(operate))
        print(' '.join(parse.get_section_options(sys.argv[3])[0]))
    elif operate == 'get_value':
        if argv_size != 5:
            sys_err(usage(operate))
        print(parse.get_value(sys.argv[3], sys.argv[4])[0])
    elif operate == 'set_value':
        if argv_size != 6:
            sys_err(usage(operate))
        parse.set_value(sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        sys_err(usage())


if __name__ == '__main__':
    main()
    sys.exit(0)

