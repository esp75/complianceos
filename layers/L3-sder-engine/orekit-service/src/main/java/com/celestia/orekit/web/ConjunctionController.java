package com.celestia.orekit.web;

import com.celestia.orekit.domain.Dtos.ConjunctionRequest;
import com.celestia.orekit.domain.Dtos.ConjunctionResponse;
import com.celestia.orekit.service.ConjunctionService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** REST surface for conjunction screening (CONTRACT.md). */
@RestController
public class ConjunctionController {

    private final ConjunctionService service;

    public ConjunctionController(ConjunctionService service) {
        this.service = service;
    }

    @PostMapping("/conjunction")
    public ConjunctionResponse conjunction(@RequestBody ConjunctionRequest request) {
        return service.screen(request);
    }
}
