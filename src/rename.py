#!/usr/bin/env python
r'''%prog [OPTIONS] [ARGS ...]

For the following examples, assume we have a directory /var/photos which
looks like this:

    $ ls -1 /var/photos
    FOO123.JPG
    IMG1010.JPG
    IMG1011.JPG
    IMG1012.JPG
    IMG_XYZ.JPG
    
Example #1 - regex:

    $ %prog --dry-run --start 7 --width 3 --increment 2 --regex "IMG(\d\d)(\d+).*" "foo-\2-\#.jpg"  /var/photos/*
    > /var/photos/IMG1010.JPG -> /var/photos/foo-10-007.jpg
    > /var/photos/IMG1011.JPG -> /var/photos/foo-11-009.jpg
    > /var/photos/IMG1012.JPG -> /var/photos/foo-12-011.jpg

Example #2 - lowercase file names

    $ %prog --dry-run --lower  /var/photos/*
    > /var/photos/FOO123.JPG -> /var/photos/foo123.jpg
    > /var/photos/IMG1010.JPG -> /var/photos/img1010.jpg
    > /var/photos/IMG1011.JPG -> /var/photos/img1011.jpg
    > /var/photos/IMG1012.JPG -> /var/photos/img1012.jpg
    > /var/photos/IMG_XYZ.JPG -> /var/photos/img_xyz.jpg

Example #3 - complex regex:

    $ %prog -dry-run -width 2 --lower --normalize --regex "" "\@-\#.jpg" Sailing\ 5\:12/
    > Sailing 5:12/P1000354.JPG -> Sailing 5:12/sailing-5-12-001.jpg
    > Sailing 5:12/P1000355.JPG -> Sailing 5:12/sailing-5-12-002.jpg
    > Sailing 5:12/P1000357.JPG -> Sailing 5:12/sailing-5-12-003.jpg
    
'''

import re, sys, os
from optparse import OptionParser, OptionGroup

DEBUG = False


#-------------------------------------------------------------------------------
def _verbose(*args):
    print >> sys.stderr, '> %s' % (' '.join(['%s' % a for a in args]),)


#-------------------------------------------------------------------------------
def _noop(*args): pass

#-------------------------------------------------------------------------------
def get_files(dirname):
    files = []
    for fn in os.listdir(dirname):
        fn = os.path.join(dirname, fn)
        if fn[0] != '.' and os.path.isfile(fn):
            files.append(fn)

    return files


#===============================================================================
class RenameError(Exception):
    pass


#===============================================================================
class SkipRename(Exception):
    pass


#===============================================================================
class FileObj(object):
    
    #---------------------------------------------------------------------------
    def __init__(self, fn):
        self.__original = fn
        self.__original_fqn = os.path.abspath(os.path.expanduser(fn))
        self.__path, self.__filename = os.path.split(self.__original_fqn)
        _, self.__parent = self.__path.split(self.__path)
        self.base, self.ext = os.path.splitext(self.__filename)
        
    #---------------------------------------------------------------------------
    @property
    def path(self):
        return self.__path
        
    #---------------------------------------------------------------------------
    @property
    def parent(self):
        return self.__parent
        
    #---------------------------------------------------------------------------
    @property
    def fqn(self):
        return '%s.%s' % (
            os.path.join(self.__path, self.__parent, self.base),
            self.ext
        )


#===============================================================================
class Rename(object):

    increment_re = re.compile(r'(?<!\\)\\#')
    dir_name_re  = re.compile(r'(?<!\\)\\@')
    normalize_re = re.compile(r'[\W]+')
    
    #---------------------------------------------------------------------------
    def __init__(
        self,
        number=1,
        ext=None,
        transform=None,
        regex=None,
        repl=None,
        increment=1,
        width=2,
        normalize=None,
        special=None,
        stream=None
    ):
        self.verbose   = stream or _noop
        self.ext       = '.%s' % ext if ext and not ext.startswith('.') else None
        self.number    = number
        self.regex     = regex
        self.repl      = repl
        self.increment = increment
        self.width     = width
        self.transform = transform
        self.normalize = normalize
        self.special   = special
        self.cwd_name  = os.path.split(os.getcwd())[1]
    
    #---------------------------------------------------------------------------
    def _default_normalizer(self, name):
        name, ext = os.path.splitext(name)
        name = '-'.join(self.normalize_re.split(name))
        return name + ext
    
    #---------------------------------------------------------------------------
    def _process_file_name(self, old_name):
        pth, fname = os.path.split(old_name)
        _, dir_name = os.path.split(pth)
        
        if not dir_name:
            if self.special:
                raise SkipRename('... ARG "%s" is not a directory' % (old_name,))
                
            dir_name = self.cwd_name
            
        num_str = '%0*d' % (self.width, self.current_number)
        new_name = fname
        
        if self.special:
            new_name = self._default_normalizer(dir_name).lower()
            _, ext = os.path.splitext(fname)
            if ext:
                ext = ext.lower()
                
            new_name = '%s-%s%s' % (new_name, num_str, ext)
        else:
            if self.regex:
                if self.regex.search(new_name):
                    self.verbose('... Regex matched: %s' % new_name)
                    new_name = self.regex.sub(self.repl, new_name)
                    new_name = self.dir_name_re.sub(dir_name, new_name)
                    new_name = self.increment_re.sub(num_str, new_name)
                else:
                    self.verbose('... NO Regex match: %s' % new_name)
        
            if self.normalize:
                fn = self.normalize if callable(self.normalize) else self._default_normalizer
                new_name = fn(new_name)
            
            if self.transform:
                new_name = self.transform(new_name)

            if self.ext:
                new_name, _ = os.path.splitext(new_name)
                new_name = new_name + self.ext

        new_name = os.path.join(pth, new_name)
        if new_name == old_name:
            raise SkipRename('... Skipped (no change): %s' % new_name)
        else:
            if os.path.exists(new_name) and not os.path.samefile(old_name, new_name):
                raise SkipRename('... Skipped (file exists): %s' % new_name)
            else:
                self.current_number += self.increment
                return (old_name, new_name)
    
    #---------------------------------------------------------------------------
    def build(self, args):
        count  = 0
        args = list(args)
        args_count = len(args)
        self.width = self.width or args_count
        self.current_number = self.number
        while args:
            old_name = args.pop(0)
            if os.path.isdir(old_name):
                args_count -= 1
                dir_files = get_files(old_name)
                if dir_files:
                    args_count += len(dir_files)
                    self.verbose('... Including directory: %s (contains %d file(s))' % (old_name, len(dir_files)))
                    args = dir_files + args
                else:
                    self.verbose('... Skipped directory (no files): %s' % old_name)

                continue
            
            try:
                yield self._process_file_name(old_name)
                count += 1
            except SkipRename, why:
                self.verbose('%s' % why)

        self.verbose('Renamed %d of %d' % (count, args_count))

    #---------------------------------------------------------------------------
    def rename(self, args):
        for old, new in args:
            os.rename(old, new)
            
    #---------------------------------------------------------------------------
    def __call__(self, args):
        self.rename(self.build(args))


#-------------------------------------------------------------------------------
def parse_opts():
    parser = OptionParser(usage=__doc__)
    parser.add_option(
        '-e', 
        '--ext', 
        dest='ext',
        help='replaces the file name extension with the given value',
        default=None
    )

    parser.add_option(
        '-C',
        '--capitalize', 
        dest='capitalize',
        help='capitalize the file name.',
        action='store_true',
        default=False
    )

    parser.add_option(
        '-U',
        '--upper', 
        dest='upper',
        help='Uppercase the file name.',
        action='store_true',
        default=False
    )

    parser.add_option(
        '-l',
        '--lower', 
        dest='lower',
        help='lowercase the file name.',
        action='store_true',
        default=False
    )

    parser.add_option(
        '-z',
        '--normalize', 
        dest='normalize',
        help='normalize the file name: all whitespace and non-alphanumeric are removed and replaced with dashes.',
        action='store_true',
        default=False
    )

    parser.add_option(
        '-x',
        '--special', 
        dest='special',
        help='special case: all arguments must be directory names, all files changed to normalized, lowercase version of directory name with auto increment.',
        action='store_true',
        default=False
    )

    parser.add_option(
        '-n',
        '--dry-run',
        dest='dry_run',
        help='Don\'t actually rename the file(s), just show what the resultant name change will be.',
        action='store_true',
        default=False
    )
    
    parser.add_option(
        '-v',
        '--verbose',
        dest='verbose',
        help='Show verbose output',
        action='store_true',
        default=False
    )

    if DEBUG:
        parser.add_option(
            '--pdb',
            dest='pdb',
            help='Start interactive debugger',
            action='store_true',
            default=False
        )
        
    parser.add_option(
        '-r', 
        '--regex', 
        dest='regex',
        help=(
            r'indicates regular expression replacement: 1st arg is regex, 2nd arg '
             'is replacement expression; replacement string may contain \#, which '
             'will be substituted as the current incremental value, or \@, which '
             'will be sbustituted as the file\'s parent directory name.'
        ),
        action='store_true',
        default=False
    )
    
    regex_group = OptionGroup(parser, 'Regex Options','Only applicable with -r/--regex option')
    regex_group.add_option(
        '-s', 
        '--start', 
        dest='number',
        help='starting counter, defaults to 1',
        type='int',
        default=1
    )

    regex_group.add_option(
        '-i', 
        '--increment', 
        dest='increment',
        help='amount by which to increment the counter',
        type='int',
        default=1
    )

    regex_group.add_option(
        '-w', 
        '--width', 
        dest='width',
        help='zero pad the counter when using \#',
        type='int',
        default=2
    )
    
    parser.add_option_group(regex_group)

    return parser.parse_args()


#-------------------------------------------------------------------------------
def main():
    
    options, args = parse_opts()
    verbose = _verbose if options.verbose or DEBUG else _noop
    dry_run = _verbose if options.dry_run else _noop
    
    if DEBUG and options.pdb:
        import pdb; pdb.set_trace()
    
    transform = None
    if options.upper:
        transform = str.upper
    elif options.lower:
        transform = str.lower
    elif options.capitalize:
        transform = str.capitalize
    
    regex = options.regex
    if regex:
        if len(args) < 3:
            raise RenameError('Need at least 3 arguments for regex, replacement, and files')

        regex, repl = args[:2]
        args = args[2:]
        if DEBUG:
            verbose('REGEX: %s' % (regex,))
            verbose('LEN:   %d' % (len(regex,)))
            verbose('REPL:  %s' % (repl,))
            
        regex = re.compile(regex or '.*')
    else:
        regex, repl = None, None
    
    
    renamer = Rename(
        number=options.number,
        ext=options.ext,
        transform=transform,
        regex=regex,
        repl=repl,
        increment=options.increment,
        width=options.width,
        normalize=options.normalize,
        special=options.special,
        stream=verbose
    )
    
    if options.dry_run:
        verbose('** DRY RUN ** Files are not renamed!')
        for old, new in renamer.build(args):
            dry_run('%s -> %s' % (old, new))
    else:
        renamer(args)


################################################################################
if __name__ == '__main__':
    try:
        main()
    except RenameError, why:
        sys.stderr.write('Error: %s\n' % why)
        sys.exit(1)
    except Exception, why:
        sys.stderr.write('Unexpected Error: %s\n' % why)
        sys.exit(2)
    else:
        sys.exit(0)

