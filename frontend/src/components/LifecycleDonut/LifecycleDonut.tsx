import React from "react";
import "./LifecycleDonut.css";

interface LifecycleDonutProps {
    score: number;
    size?: number;
    showLabel?: boolean;
}

export default function LifecycleDonut({ score, size = 48, showLabel = true }: LifecycleDonutProps) {
    const strokeWidth = size <= 32 ? 3 : 4;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const filled = circumference * score;
    const empty = circumference - filled;
    const fontSize = size <= 32 ? "8px" : "10px";

    const color =
        score >= 0.8 ? "#3fb950" :
        score >= 0.5 ? "#d29922" :
        score > 0    ? "#62a8ff" :
                       "rgba(255,255,255,0.12)";

    return (
        <div className="lifecycle-donut">
            <svg
                width={size}
                height={size}
                style={{ transform: "rotate(-90deg)" }}
            >
                <circle
                    className="lifecycle-donut__track"
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    strokeWidth={strokeWidth}
                />
                <circle
                    className="lifecycle-donut__fill"
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    strokeWidth={strokeWidth}
                    stroke={color}
                    strokeDasharray={`${filled} ${empty}`}
                />
                <text
                    className="lifecycle-donut__text"
                    x="50%"
                    y="50%"
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={fontSize}
                    fill={color}
                    style={{
                        transform: "rotate(90deg)",
                        transformOrigin: "center",
                    }}
                >
                    {Math.round(score * 100)}%
                </text>
            </svg>
            {showLabel && size > 32 && (
                <span className="lifecycle-donut__label">Progress</span>
            )}
        </div>
    );
}
