import os
import StringIO

import simplejson

from bento.core.utils import \
    subst_vars
from bento.core.pkg_objects import \
    Executable

def ipkg_meta_from_pkg(pkg):
    """Return meta dict for Installed pkg from a PackageDescription
    instance."""
    meta = {}
    for m in ["name", "version", "summary", "url", "author",
              "author_email", "license", "download_url", "description",
              "platforms", "classifiers", "install_requires", 
              "top_levels"]:
        meta[m] = getattr(pkg, m)
    return meta

class InstalledSection(object):
    @classmethod
    def from_data_files(cls, name, data_files):
        return cls("datafiles", name,
                   data_files.source_dir,
                   data_files.target_dir,
                   data_files.files)
        
    def __init__(self, tp, name, srcdir, target, files):
        self.tp = tp
        self.name = name
        self.srcdir = srcdir
        self.target = target
        self.files = files

    @property
    def fullname(self):
        return self.tp + ":" + self.name

def iter_source_files(file_sections):
    for kind in file_sections:
        if not kind in ["executables"]:
            for name, section in file_sections[kind].items():
                for f in section:
                    yield f[0]

def iter_files(file_sections):
    for kind in file_sections:
        for name, section in file_sections[kind].items():
            for source, target in section:
                yield kind, source, target

class InstalledPkgDescription(object):
    @classmethod
    def from_file(cls, filename):
        def _encode_kw(d):
            return dict([(k.encode(), v) for k, v in d.items()])

        fid = open(filename)
        try:
            data = simplejson.load(fid)
            meta_vars = _encode_kw(data["meta"])
            path_vars = data["variables"]["paths"]

            executables = {}
            for name, executable in data["variables"]["executable"].items():
                executables[name] = Executable.from_parse_dict(_encode_kw(executable))

            file_sections = {}

            def json_to_file_section(data):
                tp, section_name = data["name"].split(":", 1)
                return tp, section_name, \
                        {"files": data["files"],
                         "srcdir": data["source_dir"],
                         "target": data["target_dir"]}

            for section in data["file_sections"]:
                tp, name, files = json_to_file_section(section)
                if tp in file_sections:
                    if name in file_sections[tp]:
                        raise ValueError("section %s of type %s already exists !" % (name, type))
                    file_sections[tp][name] = files
                else:
                    file_sections[tp] = {name: files}
            return cls(file_sections, meta_vars, path_vars, executables)
        finally:
            fid.close()

    def __init__(self, files, meta, path_options, executables):
        self.files = files
        self.meta = meta
        self.path_variables = path_options
        self.executables = executables

    def write(self, filename):
        def executable_to_json(executable):
            return {"name": executable.name,
                    "module": executable.module,
                    "function": executable.function}

        def section_to_json(section):
            return {"name": section.fullname,
                    "source_dir": section.srcdir,
                    "target_dir": section.target,
                    "files": section.files}

        fid = open(filename, "w")
        try:
            data = {}
            data["meta"] = self.meta

            executables = dict([(k, executable_to_json(v)) \
                                for k, v in self.executables.items()])
            variables = {"paths": self.path_variables,
                         "executable": executables}
            data["variables"] = variables

            file_sections = []
            for tp, value in self.files.items():
                if tp in ["pythonfiles"]:
                    for i in value.values():
                        i.srcdir = "$_srcrootdir"
                        file_sections.append(section_to_json(i))
                elif tp in ["datafiles", "extension", "executable"]:
                    for i in value.values():
                        file_sections.append(section_to_json(i))
                else:
                    raise ValueError("Unknown section %s" % type)
            data["file_sections"] = file_sections
            if os.environ.has_key("BENTOMAKER_PRETTY"):
                simplejson.dump(data, fid, sort_keys=True, indent=4)
            else:
                simplejson.dump(data, fid, separators=(',', ':'))
        finally:
            fid.close()

    def resolve_paths(self, src_root_dir="."):
        self.path_variables['_srcrootdir'] = src_root_dir

        file_sections = {}
        for tp in self.files:
            file_sections[tp] = {}
            for name, value in self.files[tp].items():
                srcdir = subst_vars(value["srcdir"], self.path_variables)
                target = subst_vars(value["target"], self.path_variables)

                file_sections[tp][name] = \
                        [(os.path.join(srcdir, f), os.path.join(target, f))
                         for f in value["files"]]

        return file_sections 