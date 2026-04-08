import React from "react";

type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>;

export default function Select(props: SelectProps) {
    return <select {...props} />;
}