#!/usr/bin/env python
import fileinput
import glob
import os
import shutil
import sys

def check_build():
    build_dirs = ['build', 'build/doctrees', 'build/html', 'build/latex', 
                  'source/_static', 'source/_templates']
    for d in build_dirs:
        try:
            os.mkdir(d)
        except OSError:
            pass

def figs():
    os.system('cd source/figures/ && python make.py')

def html():
    check_build()
    os.system('sphinx-build -b html -d build/doctrees source build/html')

def latex():
    if sys.platform != 'win32':
        # LaTeX format.
        os.system('sphinx-build -b latex -d build/doctrees source build/latex')
    
        # Produce pdf.
        os.chdir('build/latex')
    
        # Copying the makefile produced by sphinx...
        os.system('pdflatex Matplotlib_Users_Guide.tex')
        os.system('pdflatex Matplotlib_Users_Guide.tex')
        os.system('makeindex -s python.ist Matplotlib_Users_Guide.idx')
        os.system('makeindex -s python.ist modMatplotlib_Users_Guide.idx')
        os.system('pdflatex Matplotlib_Users_Guide.tex')
    
        os.chdir('../..')
    else:
        print 'latex build has not been tested on windows'

def clean():
    shutil.rmtree('build')

def all():
    figs()
    html()
    latex()


funcd = {'figs':figs,
         'html':html,
         'latex':latex,
         'clean':clean,
         'all':all,
         }


if len(sys.argv)>1:
    for arg in sys.argv[1:]:
        func = funcd.get(arg)
        if func is None:
            raise SystemExit('Do not know how to handle %s; valid args are'%(
                    arg, funcd.keys()))
        func()
else:
    all()