# encoding: utf-8

"""
.. codeauthor:: Tsuyoshi Hombashi <tsuyoshi.hombashi@gmail.com>
"""

from __future__ import absolute_import, division

import pingparsing
import pytest
import typepy
from subprocrunner import SubprocessRunner

from tcconfig._const import Tc

from .common import ASSERT_MARGIN, DEADLINE_TIME, execute_tcdel


@pytest.fixture
def device_option(request):
    return request.config.getoption("--device")


@pytest.fixture
def dst_host_option(request):
    return request.config.getoption("--dst-host")


@pytest.fixture
def dst_host_ex_option(request):
    return request.config.getoption("--dst-host-ex")


@pytest.fixture
def transmitter():
    transmitter = pingparsing.PingTransmitter()
    transmitter.ping_option = "-f -q"
    transmitter.deadline = DEADLINE_TIME

    return transmitter


@pytest.fixture
def pingparser():
    return pingparsing.PingParsing()


class Test_tcset_two_network(object):
    """
    Tests in this class are not executable on CI services.
    Execute the following command at the local environment to running tests:

      python setup.py test --addopts "--device=<test device> \n
          --dst-host=<hostname/IP-addr> --dst-host-ex=<hostname/IP-addr>"

    These tests expected to execute in the following environment:
       - Linux w/ iputils-ping package
       - English locale (for parsing ping output)
    """

    @pytest.mark.parametrize(["shaping_algo"], [
        ["htb"],
    ])
    def test_network(
            self, device_option, dst_host_option, dst_host_ex_option,
            transmitter, pingparser, shaping_algo):
        if device_option is None:
            pytest.skip("device option is null")
        if any([
                typepy.is_null_string(dst_host_option),
                typepy.is_null_string(dst_host_ex_option),
        ]):
            pytest.skip("destination host is null")

        execute_tcdel(device_option)
        delay = 100

        # tc to specific network ---
        command_list = [
            Tc.Command.TCSET,
            "--device {:s}".format(device_option),
            "--delay {:d}ms".format(delay),
            "--dst-network {:s}".format(dst_host_ex_option),
            "--shaping-algo {:s}".format(shaping_algo),
        ]
        assert SubprocessRunner(" ".join(command_list)).run() == 0

        # w/o tc network ---
        transmitter.destination_host = dst_host_option
        pingparser.parse(transmitter.ping().stdout)
        without_tc_rtt_avg = pingparser.rtt_avg

        # w/ tc network ---
        transmitter.destination_host = dst_host_ex_option
        pingparser.parse(transmitter.ping().stdout)
        with_tc_rtt_avg = pingparser.rtt_avg

        # assertion ---
        rtt_diff = with_tc_rtt_avg - without_tc_rtt_avg
        assert rtt_diff > (delay * ASSERT_MARGIN)

        # finalize ---
        execute_tcdel(device_option)
