// A pill showing a granted scope, using the human label from /api/scopes
// (falls back to the raw scope key if the catalog hasn't loaded yet).

export default function ScopeChip({ scope, catalog }) {
  const info = catalog?.[scope];
  return (
    <span className="chip" title={info?.description || scope}>
      {info?.label || scope}
    </span>
  );
}
