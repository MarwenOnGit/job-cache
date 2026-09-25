import unittest

import learn


def _job(job_id, title, description="", status="interested", starred=False,
         company="acme", role_family="swe", city="berlin"):
    return {
        "id": job_id, "title": title, "description": description, "status": status,
        "starred": starred, "company": company, "role_family": role_family,
        "city": city, "seniority": "mid", "is_startup": False, "sponsorship": "silent",
        "match_score": 0.8,
    }


class TestTokens(unittest.TestCase):
    def test_generic_title_noun_is_not_a_keyword(self):
        # "engineer" is redundant with role_family and would otherwise let one
        # over-dismissed title bleed onto every other "...Engineer" posting.
        toks = learn._tokens(_job("1", "Site Reliability Engineer"))
        self.assertNotIn("engineer", toks)

    def test_title_bigram_captures_the_specific_phrase(self):
        toks = learn._tokens(_job("1", "Site Reliability Engineer"))
        self.assertIn("site reliability", toks)
        self.assertIn("site", toks)
        self.assertIn("reliability", toks)

    def test_description_skill_keywords_are_learnable(self):
        # Description text only counts through the curated skill list — free-
        # form words from the description are deliberately not tokenized
        # (too much foreign-language / boilerplate noise at this data size).
        toks = learn._tokens(_job("1", "Backend Role", description="We use kubernetes and docker daily."))
        self.assertIn("kubernetes", toks)
        self.assertIn("docker", toks)
        self.assertNotIn("daily", toks)


class TestKeywordDamping(unittest.TestCase):
    """The exact scenario the user described: dismissing a lot of one repeated
    title shouldn't tank the score of an unrelated job that merely shares a
    common word with it."""

    def _train_sre_dismissals(self, n):
        jobs = [_job(f"neg{i}", "Site Reliability Engineer", status="dismissed") for i in range(n)]
        # A handful of unrelated jobs the user actually pursued, to give the
        # model a base rate and make it "ready".
        jobs += [_job(f"pos{i}", "AI Engineer", status="applied") for i in range(3)]
        return learn.train(jobs)

    def test_unrelated_engineer_title_is_not_penalized(self):
        model = self._train_sre_dismissals(50)
        # No "engineer" keyword weight should exist at all (it's stop-listed).
        self.assertNotIn("kw:engineer", model["weights"])
        untouched = _job("x", "Backend Engineer", description="Python APIs.")
        self.assertGreater(learn.score(untouched, model), 0.4)

    def test_weight_grows_logarithmically_not_linearly(self):
        model_50 = self._train_sre_dismissals(50)
        model_1000 = self._train_sre_dismissals(1000)
        w50 = model_50["weights"]["kw:site reliability"]
        w1000 = model_1000["weights"]["kw:site reliability"]
        self.assertLess(w1000, w50)  # more evidence -> still more negative...
        # ...but nowhere near the 20x growth in raw dismissal count.
        self.assertLess(w50 / w1000, 3.0)

    def test_keyword_weight_is_capped(self):
        model = self._train_sre_dismissals(5000)
        for key, w in model["weights"].items():
            if key.startswith("kw:"):
                self.assertLessEqual(abs(w), 1.5)

    def test_categorical_signal_still_compounds_normally(self):
        # Dismissing many jobs from one company is real, low-cardinality
        # signal — it should reach high confidence much faster than an
        # equally one-sided keyword does, since it isn't log-damped.
        jobs = [_job(f"neg{i}", f"Role {i}", status="dismissed", company="bigco") for i in range(50)]
        jobs += [_job(f"pos{i}", f"Role {i}", status="applied", company="othercorp") for i in range(3)]
        model = learn.train(jobs)
        company_w = model["weights"]["company:bigco"]

        kw_jobs = [_job(f"kneg{i}", "Site Reliability Engineer", status="dismissed") for i in range(50)]
        kw_jobs += [_job(f"kpos{i}", "AI Engineer", status="applied") for i in range(3)]
        kw_model = learn.train(kw_jobs)
        kw_w = kw_model["weights"]["kw:site reliability"]

        # Same 50-vs-3 imbalance, but the categorical facet is trusted more.
        self.assertLess(company_w, kw_w)


if __name__ == "__main__":
    unittest.main()
