#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2013 Chris Johns (chrisj@rtems.org)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-tools'.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

#
# This code builds a package given a config file. It only builds to be
# installed not to be package unless you run a packager around this.
#

import copy
import datetime
import os
import sys

try:
    import build
    import check
    import config
    import error
    import git
    import log
    import options
    import path
    import setbuilder
    import version
except KeyboardInterrupt:
    print 'user terminated'
    sys.exit(1)
except:
    print 'error: unknown application load error'
    sys.exit(1)

class report:
    """Report the build details about a package given a config file."""

    line_len = 78

    def __init__(self, format, _configs, opts, macros = None):
        self.format = format
        self.configs = _configs
        self.opts = opts
        if macros is None:
            self.macros = opts.defaults
        else:
            self.macros = macros
        self.bset_nesting = 0
        self.configs_active = False
        self.out = ''
        self.asciidoc = None

    def _sbpath(self, *args):
        p = self.macros.expand('%{_sbdir}')
        for arg in args:
            p = path.join(p, arg)
        return os.path.abspath(path.host(p))

    def output(self, text):
        self.out += '%s\n' % (text)

    def is_text(self):
        return self.format == 'text'

    def is_asciidoc(self):
        return self.format == 'asciidoc' or self.format == 'html'

    def setup(self):
        if self.format == 'html':
            try:
                import asciidocapi
            except:
                raise error.general('installation error: no asciidocapi found')
            asciidoc_py = self._sbpath(options.basepath, 'asciidoc', 'asciidoc.py')
            try:
                self.asciidoc = asciidocapi.AsciiDocAPI(asciidoc_py)
            except:
                raise error.general('application error: asciidocapi failed')

    def header(self):
        pass

    def footer(self):
        pass

    def git_status(self):
        text = 'RTEMS Source Builder Repository Status'
        if self.is_asciidoc():
            self.output('')
            self.output("'''")
            self.output('')
            self.output('.%s' % (text))
        else:
            self.output('-' * self.line_len)
            self.output('%s' % (text))
        repo = git.repo('.', self.opts, self.macros)
        repo_valid = repo.valid()
        if repo_valid:
            if self.is_asciidoc():
                self.output('*Remotes*:;;')
            else:
                self.output(' Remotes:')
            repo_remotes = repo.remotes()
            rc = 0
            for r in repo_remotes:
                rc += 1
                if 'url' in repo_remotes[r]:
                    text = repo_remotes[r]['url']
                else:
                    text = 'no URL found'
                text = '%s: %s' % (r, text)
                if self.is_asciidoc():
                    self.output('. %s' % (text))
                else:
                    self.output('  %2d: %s' % (rc, text))
            if self.is_asciidoc():
                self.output('*Status*:;;')
            else:
                self.output(' Status:')
            if repo.clean():
                if self.is_asciidoc():
                    self.output('Clean')
                else:
                    self.output('  Clean')
            else:
                if self.is_asciidoc():
                    self.output('_Repository is dirty_')
                else:
                    self.output('  Repository is dirty')
            repo_head = repo.head()
            if self.is_asciidoc():
                self.output('*Head*:;;')
                self.output('Commit: %s' % (repo_head))
            else:
                self.output(' Head:')
                self.output('  Commit: %s' % (repo_head))
        else:
            self.output('_Not a valid GIT repository_')
        if self.is_asciidoc():
            self.output('')
            self.output("'''")
            self.output('')

    def introduction(self, name, intro_text = None):
        if self.is_asciidoc():
            h = 'RTEMS Source Builder Report'
            self.output(h)
            self.output('=' * len(h))
            self.output(':doctype: book')
            self.output(':toc2:')
            self.output(':toclevels: 5')
            self.output(':icons:')
            self.output(':numbered:')
            self.output(':data-uri:')
            self.output('')
            self.output('RTEMS Tools Project <rtems-users@rtems.org>')
            self.output(datetime.datetime.now().ctime())
            self.output('')
            image = self._sbpath(options.basepath, 'images', 'rtemswhitebg.jpg')
            self.output('image:%s["RTEMS",width="20%%"]' % (image))
            self.output('')
            if intro_text:
                self.output('%s' % ('\n'.join(intro_text)))
        else:
            self.output('=' * self.line_len)
            self.output('RTEMS Tools Project <rtems-users@rtems.org> %s' % datetime.datetime.now().ctime())
            if intro_text:
                self.output('')
                self.output('%s' % ('\n'.join(intro_text)))
            self.output('=' * self.line_len)
            self.output('Report: %s' % (name))
        self.git_status()

    def config_start(self, name):
        first = not self.configs_active
        self.configs_active = True

    def config_end(self, name):
        if self.is_asciidoc():
            self.output('')
            self.output("'''")
            self.output('')

    def buildset_start(self, name):
        if self.is_asciidoc():
            h = '%s' % (name)
            self.output('=%s %s' % ('=' * self.bset_nesting, h))
        else:
            self.output('=-' * (self.line_len / 2))
            self.output('Build Set: %s' % (name))

    def buildset_end(self, name):
        self.configs_active = False

    def source(self, package, source_tag):
        return package.sources()

    def patch(self, package, args):
        return package.patches()

    def output_info(self, name, info, separated = False):
        if info is not None:
            end = ''
            if self.is_asciidoc():
                if separated:
                    self.output('*%s:*::' % (name))
                    self.output('')
                else:
                    self.output('*%s:* ' % (name))
                    end = ' +'
                spaces = ''
            else:
                self.output(' %s:' % (name))
                spaces = '  '
            for l in info:
                self.output('%s%s%s' % (spaces, l, end))
            if self.is_asciidoc() and separated:
                self.output('')

    def output_directive(self, name, directive):
        if directive is not None:
            if self.is_asciidoc():
                self.output('')
                self.output('*%s*:' % (name))
                self.output('--------------------------------------------')
                spaces = ''
            else:
                self.output(' %s:' % (name))
                spaces = '  '
            for l in directive:
                self.output('%s%s' % (spaces, l))
            if self.is_asciidoc():
                self.output('--------------------------------------------')

    def config(self, _config, opts, macros):

        packages = _config.packages()
        package = packages['main']
        name = package.name()
        self.config_start(name)
        if self.is_asciidoc():
            self.output('*Package*: _%s_ +' % (name))
            self.output('*Config*: %s' % (_config.file_name()))
            self.output('')
        else:
            self.output('-' * self.line_len)
            self.output('Package: %s' % (name))
            self.output(' Config: %s' % (_config.file_name()))
        self.output_info('Summary', package.get_info('summary'), True)
        self.output_info('URL', package.get_info('url'))
        self.output_info('Version', package.get_info('version'))
        self.output_info('Release', package.get_info('release'))
        self.output_info('Build Arch', package.get_info('buildarch'))
        if self.is_asciidoc():
            self.output('')
        sources = package.sources()
        if self.is_asciidoc():
            self.output('*Sources:*::')
            if len(sources) == 0:
                self.output('No sources')
        else:
            self.output('  Sources: %d' % (len(sources)))
        c = 0
        for s in sources:
            c += 1
            if self.is_asciidoc():
                self.output('. %s' % (sources[s][0]))
            else:
                self.output('   %2d: %s' % (c, sources[s][0]))
        patches = package.patches()
        if self.is_asciidoc():
            self.output('')
            self.output('*Patches:*::')
            if len(patches) == 0:
                self.output('No patches')
        else:
            self.output('  Patches: %s' % (len(patches)))
        c = 0
        for p in patches:
            c += 1
            if self.is_asciidoc():
                self.output('. %s' % (patches[p][0]))
            else:
                self.output('   %2d: %s' % (c, patches[p][0]))
        self.output_directive('Preparation', package.prep())
        self.output_directive('Build', package.build())
        self.output_directive('Install', package.install())
        self.output_directive('Clean', package.clean())
        self.config_end(name)

    def write(self, name):
        if self.format == 'html':
            if self.asciidoc is None:
                raise error.general('asciidoc not initialised')
            import StringIO
            infile = StringIO.StringIO(self.out)
            outfile = StringIO.StringIO()
            self.asciidoc.execute(infile, outfile)
            self.out = outfile.getvalue()
            infile.close()
            outfile.close()
        if name is not None:
            try:
                o = open(path.host(name), "w")
                o.write(self.out)
                o.close()
                del o
            except IOError, err:
                raise error.general('writing output file: %s: %s' % (name, err))

    def generate(self, name, opts = None, macros = None):
        self.bset_nesting += 1
        self.buildset_start(name)
        if opts is None:
            opts = self.opts
        if macros is None:
            macros = self.macros
        bset = setbuilder.buildset(name, self.configs, opts, macros)
        for c in bset.load():
            if c.endswith('.bset'):
                self.buildset(c, bset.opts, bset.macros)
            elif c.endswith('.cfg'):
                self.config(config.file(c, bset.opts, bset.macros),
                            bset.opts, bset.macros)
            else:
                raise error.general('invalid config type: %s' % (c))
        self.buildset_end(name)
        self.bset_nesting -= 1

    def create(self, inname, outname = None, intro_text = None):
        self.setup()
        self.introduction(inname, intro_text)
        self.generate(inname)
        self.write(outname)

def run(args):
    try:
        optargs = { '--list-bsets':   'List available build sets',
                    '--list-configs': 'List available configurations',
                    '--format':       'Output format (text, html, asciidoc)',
                    '--output':       'File name to output the report' }
        opts = options.load(args, optargs)
        if opts.get_arg('--output') and len(opts.params()) > 1:
            raise error.general('--output can only be used with a single config')
        print 'RTEMS Source Builder, Reporter v%s' % (version.str())
        opts.log_info()
        if not check.host_setup(opts):
            log.warning('forcing build with known host setup problems')
        configs = build.get_configs(opts)
        if not setbuilder.list_bset_cfg_files(opts, configs):
            output = opts.get_arg('--output')
            if output is not None:
                output = output[1]
            format = 'text'
            ext = '.txt'
            format_opt = opts.get_arg('--format')
            if format_opt:
                if len(format_opt) != 2:
                    raise error.general('invalid format option: %s' % ('='.join(format_opt)))
                if format_opt[1] == 'text':
                    pass
                elif format_opt[1] == 'asciidoc':
                    format = 'asciidoc'
                    ext = '.txt'
                elif format_opt[1] == 'html':
                    format = 'html'
                    ext = '.html'
                else:
                    raise error.general('invalid format: %s' % (format_opt[1]))
            r = report(format, configs, opts)
            for _config in opts.params():
                if output is None:
                    outname = path.splitext(_config)[0] + ext
                    outname = outname.replace('/', '-')
                else:
                    outname = output
                config = build.find_config(_config, configs)
                if config is None:
                    raise error.general('config file not found: %s' % (inname))
                r.create(config, outname)
            del r
        else:
            raise error.general('invalid config type: %s' % (config))
    except error.general, gerr:
        print gerr
        sys.exit(1)
    except error.internal, ierr:
        print ierr
        sys.exit(1)
    except error.exit, eerr:
        pass
    except KeyboardInterrupt:
        log.notice('abort: user terminated')
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    run(sys.argv)
