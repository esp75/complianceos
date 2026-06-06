package com.celestia.orekit.error;

/**
 * An error that maps to the CONTRACT.md envelope with an explicit code
 * (invalid_tle / invalid_frame / invalid_window / invalid_request). Thrown by the
 * services; turned into a 400 by {@code GlobalExceptionHandler}. Lives in its own
 * package so both {@code service} and {@code web} can depend on it without a cycle.
 */
public class ApiException extends RuntimeException {

    private final String code;

    public ApiException(String code, String message) {
        super(message);
        this.code = code;
    }

    public String code() {
        return code;
    }
}
