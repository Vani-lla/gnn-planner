import React from "react";
import "../styles/Background.css"; // import the CSS for background styles

export const Background = ({ children }) => {
  return (
    <div className="bg-pattern">
      <div className="bg-overlay"></div>
      <div className="bg-grid"></div>
      <div className="bg-content">{children}</div>
    </div>
  );
};
