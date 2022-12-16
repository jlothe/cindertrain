#!/usr/bin/env python
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections
import os
import subprocess
import textwrap

from cinder.volume import configuration
from cinder.compute import nova

OrderedDict = collections.OrderedDict

BASEDIR = os.path.split(os.path.realpath(__file__))[0] + "/../../"


if __name__ == "__main__":
    os.chdir(BASEDIR)
    opt_file = open("cinder/opts.py", 'w')
    opt_dict = OrderedDict()
    dir_trees_list = []
    REGISTER_OPTS_STR = "CONF.register_opts("
    REGISTER_OPT_STR = "CONF.register_opt("

    license_str = textwrap.dedent(
        """
        # Licensed under the Apache License, Version 2.0 (the "License");
        # you may not use this file except in compliance with the License.
        # You may obtain a copy of the License at
        #
        #    http://www.apache.org/licenses/LICENSE-2.0
        #
        # Unless required by applicable law or agreed to in writing, software
        # distributed under the License is distributed on an "AS IS" BASIS,
        # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
        # implied.
        # See the License for the specific language governing permissions and
        # limitations under the License.\n
    """)
    opt_file.write(license_str)

    edit_header = textwrap.dedent(
        """
        ###################################################################
        # WARNING!
        #
        # Do not edit this file directly. This file should be generated by
        # running the command "tox -e genopts" any time a config option
        # has been added, changed, or removed.
        ###################################################################\n
    """)
    opt_file.write(edit_header)

    opt_file.write("import itertools\n\n")

    opt_file.write("from keystoneauth1 import loading\n\n")
    # NOTE(geguileo): We need to register all OVOs before importing any other
    # cinder files, otherwise any decorator that uses cinder.objects.YYY will
    # fail with exception AttributeError: 'module' object has no attribute
    # 'YYY' when running tox -egenconfig
    opt_file.write("from cinder import objects\nobjects.register_all()\n\n")

    targetdir = 'cinder'

    common_string = ('find ' + targetdir + ' -type f -name "*.py" !  '
                     '-path "*/tests/*" -exec grep -l "%s" {} '
                     '+  | sed -e "s|^' + BASEDIR +
                     '|/|g" | sort -u')

    cmd_opts = common_string % REGISTER_OPTS_STR
    output_opts = subprocess.check_output(  # nosec : command is hardcoded
        '{}'.format(cmd_opts), shell=True,
        universal_newlines=True)
    dir_trees_list = output_opts.split()

    cmd_opt = common_string % REGISTER_OPT_STR
    output_opt = subprocess.check_output(  # nosec : command is hardcoded
        '{}'.format(cmd_opt), shell=True,
        universal_newlines=True)
    temp_list = output_opt.split()

    for item in temp_list:
        dir_trees_list.append(item)
    dir_trees_list.sort()

    flag = False

    def _check_import(aline):
        if len(aline) > 79:
            new_lines = aline.partition(' as ')
            return new_lines
        else:
            return [aline]

    for atree in dir_trees_list:

        if atree in ["tools/config/generate_cinder_opts.py",
                     "cinder/tests/hacking/checks.py",
                     "cinder/volume/configuration.py",
                     "cinder/test.py",
                     "cinder/cmd/status.py"]:
            continue

        dirs_list = atree.split('/')

        import_module = "from "
        init_import_module = ""
        import_name = ""

        for dir in dirs_list:
            if dir.find(".py") == -1:
                import_module += dir + "."
                init_import_module += dir + "."
                import_name += dir + "_"
            else:
                if dir[:-3] != "__init__":
                    import_name += dir[:-3].replace("_", "")
                    import_module = (import_module[:-1] + " import " +
                                     dir[:-3] + " as " + import_name)
                    lines = _check_import(import_module)
                    if len(lines) > 1:
                        opt_file.write(lines[0] + lines[1] + "\\\n")
                        opt_file.write("    " + lines[2] + "\n")
                    else:
                        opt_file.write(lines[0] + "\n")

                else:
                    import_name = import_name[:-1].replace('/', '.')
                    init_import = atree[:-12].replace('/', '.')
                    opt_file.write("import " + init_import + "\n")

                    flag = True
        if flag is False:
            opt_dict[import_name] = atree
        else:
            opt_dict[init_import_module.strip(".")] = atree

        flag = False

    registered_opts_dict = OrderedDict([('DEFAULT', [])])

    def _write_item(opts):
        list_name = opts[-3:]
        if list_name.lower() == "opt":
            line_to_write = "                [" + opts.strip("\n") + "],\n"
            opt_line = _check_line_length(line_to_write)
            if len(opt_line) > 1:
                opt_file.write(opt_line[0] + opt_line[1] + "\n")
                opt_file.write("                    " + opt_line[2])
            else:
                opt_file.write(opt_line[0])
        else:
            line_to_write = "                " + opts.strip("\n") + ",\n"
            opt_line = _check_line_length(line_to_write)
            if len(opt_line) > 1:
                opt_file.write(opt_line[0] + opt_line[1] + "\n")
                opt_file.write("                " + opt_line[2])
            else:
                opt_file.write(opt_line[0])
        if opts.endswith('service_user_opts'):
            su_dnt = " " * 16
            su_plg = su_dnt + "loading.get_auth_plugin_conf_options"
            opt_file.write(
                su_plg + "('v3password'),\n"
                + su_dnt + "loading.get_session_conf_options(),\n")

    def _retrieve_name(aline):
        if REGISTER_OPT_STR in aline:
            str_to_replace = REGISTER_OPT_STR
        else:
            str_to_replace = REGISTER_OPTS_STR
        return aline.replace(str_to_replace, "")

    def _check_line_length(aline):
        if len(aline) > 79:
            temp = aline.split(".")
            lines_to_write = []

            for section in temp:
                lines_to_write.append(section)
                lines_to_write.append('.')

            return lines_to_write

        else:
            return [aline]

    for key in opt_dict:
        fd = os.open(opt_dict[key], os.O_RDONLY)
        afile = os.fdopen(fd, "r")

        for aline in afile:
            exists = aline.find("CONF.register_opt")
            if exists != -1:
                # TODO(kjnelson) FIX THIS LATER. These are instances where
                # CONF.register_opts is happening without actually registering
                # real lists of opts

                exists = aline.find('base_san_opts')
                if (exists != -1) or (key == 'cinder_volume_configuration'):
                    continue

                group_exists = aline.find(', group=')
                formatted_opt = _retrieve_name(aline[: group_exists])
                formatted_opt = formatted_opt.replace(')', '').strip()
                if group_exists != -1:
                    group_name = aline[group_exists:-1].replace(
                        ', group=\"\'', '').replace(
                        ', group=', '').strip(
                        "\'\")").upper()

                    # NOTE(dulek): Hack to resolve constants manually.
                    if (group_name.endswith('SHARED_CONF_GROUP')
                            or group_name.lower() == 'backend_defaults'):
                        group_name = configuration.SHARED_CONF_GROUP
                    if (group_name == 'NOVA_GROUP'):
                        group_name = nova.NOVA_GROUP

                    if group_name in registered_opts_dict:
                        line = key + "." + formatted_opt
                        registered_opts_dict[group_name].append(line)
                    else:
                        line = key + "." + formatted_opt
                        registered_opts_dict[group_name] = [line]
                else:
                    line = key + "." + formatted_opt
                    registered_opts_dict['DEFAULT'].append(line)

    setup_str = ("\n\n"
                 "def list_opts():\n"
                 "    return [\n")
    opt_file.write(setup_str)

    registered_opts_dict = OrderedDict(sorted(registered_opts_dict.items(),
                                              key = lambda x: x[0]))

    for key in registered_opts_dict:
        # NOTE(jsbryant): We need to have 'DEFAULT' in uppercase but any
        # other section using uppercase causes a Sphinx warning.
        if (key == 'DEFAULT'):
            section_start_str = ("        ('" + key + "',\n"
                                 "            itertools.chain(\n")
        else:
           section_start_str = ("        ('" + key.lower() + "',\n"
                                "            itertools.chain(\n")
        opt_file.write(section_start_str)
        for item in registered_opts_dict[key]:
            _write_item(item)
        section_end_str = "            )),\n"
        opt_file.write(section_end_str)

    closing_str = ("    ]\n")
    opt_file.write(closing_str)
    opt_file.close()