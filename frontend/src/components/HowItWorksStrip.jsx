import { Fragment } from "react";

import Icon from "./Icon.jsx";

// A compact horizontal "How it works" strip: numbered, icon-led steps joined by
// arrows. Shared by the Explore pages so each one opens with the same
// orientation ritual. `steps` is a list of [icon, title, body].
export default function HowItWorksStrip({ steps, title = "How it works" }) {
  return (
    <div className="card hiw">
      <h3 className="hiw-title">{title}</h3>
      <div className="hiw-steps">
        {steps.map(([icon, heading, body], i) => (
          <Fragment key={heading}>
            <div className="hiw-step">
              <div className="hiw-top">
                <span className="hiw-num">{i + 1}</span>
                <span className="hiw-icon">
                  <Icon name={icon} />
                </span>
              </div>
              <strong>{heading}</strong>
              <span className="section-note">{body}</span>
            </div>
            {i < steps.length - 1 && (
              <span className="hiw-arrow" aria-hidden="true">
                <Icon name="arrowRight" />
              </span>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
