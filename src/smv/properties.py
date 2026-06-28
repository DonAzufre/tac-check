PROPERTIES = [
    ("BothEventuallyStop", "AF ((src_done | src_trap) & (opt_done | opt_trap))"),
    ("SameNormalOutput", "AG ((src_done & opt_done) -> src_out = opt_out)"),
    ("SameTrapBehavior1", "AG (src_trap -> AF opt_trap)"),
    ("SameTrapBehavior2", "AG (opt_trap -> AF src_trap)"),
    (
        "NoMismatchAtStop",
        "AG (((src_done | src_trap) & (opt_done | opt_trap)) -> ((src_done & opt_done & src_out = opt_out) | (src_trap & opt_trap)))",
    ),
    ("NoTimeout", "AG !(src_timeout | opt_timeout)"),
]
