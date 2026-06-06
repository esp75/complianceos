package com.celestia.orekit.web;

/**
 * The uniform error envelope from CONTRACT.md: {@code {"error":{"code","message"}}}.
 * One shape so the Python {@code OrekitClient} has a single thing to parse.
 */
public record ErrorResponse(ErrorBody error) {

    public record ErrorBody(String code, String message) {}

    public static ErrorResponse of(String code, String message) {
        return new ErrorResponse(new ErrorBody(code, message));
    }
}
