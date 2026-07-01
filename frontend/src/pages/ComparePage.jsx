import { useEffect, useState } from "react";

import { getComparison } from "../api.js";
import { SkeletonCard } from "../components/Skeleton.jsx";

// The old-way/new-way contrast (item-20): screen-scraping vs token-based FDX
// access, dimension by dimension, from the backend comparison data.
export default function ComparePage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getComparison()
      .then(setRows)
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  if (error) return <div className="error">{error}</div>;

  return (
    <section>
      <h2>Old way vs new way</h2>
      <p className="section-note">
        Most account aggregation in Canada still logs into your bank with your saved password and
        scrapes the HTML. FDX open banking replaces that with scoped, revocable, token-based access —
        the model this project is built on. Here is the contrast, dimension by dimension.
      </p>

      {loading ? (
        <SkeletonCard lines={6} />
      ) : (
        <div className="compare">
          <div className="compare-row compare-head">
            <div className="compare-col-dim" />
            <div className="compare-col-old">Screen-scraping · the old way</div>
            <div className="compare-col-new">FDX open banking · the new way</div>
          </div>
          {rows.map((r) => (
            <div className="compare-row" key={r.dimension}>
              <div className="compare-dim">{r.dimension}</div>
              <div className="compare-old">
                <span className="mark mark-old" aria-hidden="true">
                  ✕
                </span>
                {r.screenScraping}
              </div>
              <div className="compare-new">
                <span className="mark mark-new" aria-hidden="true">
                  ✓
                </span>
                {r.fdxOpenBanking}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
