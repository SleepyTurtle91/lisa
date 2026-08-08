public class SessionTest {
    @Test
    public void testExecution() {
        SessionContext context = new SessionContext();
        context.setExecution(new ExecutionImpl());
        context.run();
    }
}