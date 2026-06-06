package com.celestia.orekit.web;

import com.celestia.orekit.domain.Dtos.FrameConvertRequest;
import com.celestia.orekit.domain.Dtos.PropagateRequest;
import com.celestia.orekit.domain.Dtos.StateVectorResponse;
import com.celestia.orekit.service.PropagationService;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** REST surface for propagation and frame conversion (CONTRACT.md). */
@RestController
public class PropagationController {

    private final PropagationService service;

    public PropagationController(PropagationService service) {
        this.service = service;
    }

    @PostMapping("/propagate")
    public StateVectorResponse propagate(@RequestBody PropagateRequest request) {
        return service.propagate(request);
    }

    @PostMapping("/frame_convert")
    public StateVectorResponse frameConvert(@RequestBody FrameConvertRequest request) {
        return service.convertFrame(request.state(), request.fromFrame(), request.toFrame());
    }
}
