"""Synthetic tests for figure plotting script."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.plot_w1_audit_figures import (
    plot_domain_distribution,
    plot_safety_distribution,
    plot_platform_by_domain,
    main,
)


class TestFigurePlotting(unittest.TestCase):
    def test_plot_generation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            p1 = tmp_path / "w1_domain_distribution.png"
            p2 = tmp_path / "w1_safety_distribution.png"
            p3 = tmp_path / "w1_platform_by_domain.png"

            plot_domain_distribution(p1)
            plot_safety_distribution(p2)
            plot_platform_by_domain(p3)

            self.assertTrue(p1.exists())
            self.assertTrue(p2.exists())
            self.assertTrue(p3.exists())
            self.assertGreater(p1.stat().st_size, 1000)
            self.assertGreater(p2.stat().st_size, 1000)
            self.assertGreater(p3.stat().st_size, 1000)

    def test_main_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ret = main(["--output-dir", tmpdir])
            self.assertEqual(ret, 0)
            self.assertTrue((Path(tmpdir) / "w1_domain_distribution.png").exists())


if __name__ == "__main__":
    unittest.main()
