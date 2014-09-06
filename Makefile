#----------------------------------------------------------------------------
#  Copyright (C) 2008-2014, IPython Development Team and Enthought, Inc.
#  Distributed under the terms of the BSD License.  See COPYING.rst.
#----------------------------------------------------------------------------

PYTHON := python
PYTHON_VERSION := $(shell ${PYTHON} --version 2>&1 | cut -f 2 -d ' ')

COVERAGE := coverage

MPIEXEC := mpiexec

NPROCS := 12

PARALLEL_OUT_DIR := .parallel_out

PARALLEL_UNITTEST_ARGS := -m unittest discover -s distarray/localapi/tests -p 'paralleltest*.py'
PARALLEL_TEST_REGULAR := ${PYTHON} ${PARALLEL_UNITTEST_ARGS}
PARALLEL_TEST_COVERAGE := ${COVERAGE} run -p ${PARALLEL_UNITTEST_ARGS}

MPI_OUT_BASE := unittest.out
MPI_OUT_PREFIX := ${PARALLEL_OUT_DIR}/${PYTHON_VERSION}-${MPI_OUT_BASE}


MPI_ONLY_LAUNCH_TEST := mpiexec -np 5 python ./distarray/globalapi/tests/launch_mpi.py 

# see if we're using MPICH2, else assume OpenMPI
ifneq (,$(findstring MPICH2,$(shell mpicc -v 2>&1)))
    MPIEXEC_ARGS := --outfile-pattern ${MPI_OUT_PREFIX}.%r.stdout \
                    --errfile-pattern ${MPI_OUT_PREFIX}.%r.stderr \
                    -n ${NPROCS}
else
    MPIEXEC_ARGS := --output-filename ${MPI_OUT_PREFIX} -n ${NPROCS}
endif


# Inside MPI_EXEC_CMD, PARALLEL_TEST is meant to be substituted with either
# PARALLEL_TEST_REGULAR or PARALLEL_TEST_COVERAGE from above.  See the
# `test_engines` and `test_engines_with_coverage` targets.
MPI_EXEC_CMD = (${MPIEXEC} ${MPIEXEC_ARGS} ${PARALLEL_TEST} ; OUT=$$? ; \
			   for f in ${MPI_OUT_PREFIX}* ; do echo "====> " $$f ; tail -1 $$f ; done ; \
			   exit $$OUT)

# default number of engines to use.
NENGINES := 4

# ----------------------------------------------------------------------------
#  Installation targets.
# ----------------------------------------------------------------------------

develop:
	${PYTHON} setup.py develop
.PHONY: develop

install:
	${PYTHON} setup.py install
.PHONY: install

# ----------------------------------------------------------------------------
#  Testing-related targets.
# ----------------------------------------------------------------------------

test_ipython:
	${PYTHON} -m unittest discover -c
.PHONY: test_ipython

test_ipython_with_coverage:
	${COVERAGE} run -pm unittest discover -cv
.PHONY: test_ipython_with_coverage

${PARALLEL_OUT_DIR} :
	mkdir ${PARALLEL_OUT_DIR}

test_engines: ${PARALLEL_OUT_DIR}
	@-${RM} ${MPI_OUT_PREFIX}*
	$(eval PARALLEL_TEST := ${PARALLEL_TEST_REGULAR})
	@echo "Running '${PARALLEL_TEST}' on each engine..."
	@${MPI_EXEC_CMD}
.PHONY: test_engines

test_engines_with_coverage: ${PARALLEL_OUT_DIR}
	@-${RM} ${MPI_OUT_PREFIX}*
	$(eval PARALLEL_TEST := ${PARALLEL_TEST_COVERAGE})
	@echo "Running '${PARALLEL_TEST}' on each engine..."
	@${MPI_EXEC_CMD}
.PHONY: test_engines_with_coverage

test_mpi:
	mpiexec -np 1 python -m unittest discover -c : -np 4 distarray/apps/engine.py
	${MPI_ONLY_LAUNCH_TEST}
.PHONY: test_mpi

test_mpi_with_coverage:
	mpiexec -np 1 ${COVERAGE} run -m unittest discover -c : -np 4 ${COVERAGE} run distarray/apps/engine.py
	${MPI_ONLY_LAUNCH_TEST}
.PHONY: test_mpi_with_coverage

test: test_ipython test_mpi test_engines
.PHONY: test

test_with_coverage: test_ipython_with_coverage test_mpi_with_coverage test_engines_with_coverage 
.PHONY: test_with_coverage

coverage_report:
	${COVERAGE} combine
	${COVERAGE} html
.PHONY: coverage_report

# ----------------------------------------------------------------------------
#  Cleanup.
# ----------------------------------------------------------------------------

clean:
	-${PYTHON} setup.py clean --all
	-find . \( -iname '*.py[co]' -or -iname '*.so' -or -iname '*.c' -or -iname '__pycache__' -or -iname '.ipynb_checkpoints' \) -exec ${RM} -r '{}' +
	-${RM} -r ${PARALLEL_OUT_DIR} build coverage_report examples/julia_set/build
	-${MAKE} clean -C docs
.PHONY: clean

cleanall: clean
	-${RM} -r MANIFEST dist distarray.egg-info
.PHONY: cleanall
